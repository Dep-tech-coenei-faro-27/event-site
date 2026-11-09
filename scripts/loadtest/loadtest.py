"""Load test of the backend: sign-ins, purchases, live payment streams, sign-ups.

Only the standard library for HTTP, so the client side stays simple and predictable;
``--db-url`` (PostgreSQL) adds the database checks and needs ``psycopg2``, which the
backend's virtual environment has. ``run.sh`` prepares a database, starts the server
and calls this script; see ``README.md``.

The target is ``http://127.0.0.1:8000`` unless ``--base`` says otherwise, and any host
that is not this machine also needs ``--remote``: a load test never reaches a real
server by accident. Every virtual person sends its own ``X-Forwarded-For`` (uvicorn
trusts it from 127.0.0.1), so the per-IP limits see 300 people and not one, except in
the ``campus`` scenario, where they all share one address like behind a campus NAT.

Scenarios (``--users`` people spread over ``--over`` seconds):
  login     each person signs in (bcrypt).
  payments  each person, already signed in, starts a purchase and then follows its
            live status (SSE) until it is decided, like the waiting screen.
  sse       each person, with a payment waiting, opens its live stream at the same time
            and keeps it open until the payment is decided (or ``--hold`` seconds).
  register  new accounts; then waits for the email queue to empty (``--db-url``).
  mix       payments + sign-ins + sign-ups + reads of the modalities, all together.
  campus    everyone reads the modalities and signs in from one IP.
"""

import argparse
import http.client
import ipaddress
import json
import statistics
import sys
import threading
import time
import urllib.parse
from collections import Counter
from pathlib import Path

EMAIL_PATTERN = "load-{:04d}@loadtest.example.com"
PASSWORD = "LoadTest-2027!"
PHONE = "912345678"
CAMPUS_IP = "193.136.224.10"
FINAL_STATUSES = {"confirmed", "failed", "expired", "refunded", "refund_due"}
READY_SLOW_SECONDS = 1.0
# Cloudflare gives up on an answer after 100 s, and so does the browser behind it.
CLIENT_TIMEOUT_SECONDS = 100


class Target:
    def __init__(self, base: str) -> None:
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise SystemExit(f"--base must look like http://127.0.0.1:8000: {base!r}")
        self.https = parsed.scheme == "https"
        self.host = parsed.hostname
        self.port = parsed.port or (443 if self.https else 80)

    @property
    def is_local(self) -> bool:
        if self.host == "localhost":
            return True
        try:
            return ipaddress.ip_address(self.host).is_loopback
        except ValueError:
            return False

    def connect(self, timeout: float) -> http.client.HTTPConnection:
        cls = http.client.HTTPSConnection if self.https else http.client.HTTPConnection
        return cls(self.host, self.port, timeout=timeout)


class Recorder:
    """Every request: when it started (seconds since the test began), what it was,
    the status (0 when there was no answer) and how long it took."""

    def __init__(self) -> None:
        self.start = time.monotonic()
        self.rows: list[dict] = []
        self._lock = threading.Lock()

    def now(self) -> float:
        return time.monotonic() - self.start

    def add(self, op: str, started: float, status: int, seconds: float, **extra):
        row = {"t": round(started, 3), "op": op, "status": status}
        row["ms"] = round(seconds * 1000, 1)
        row.update(extra)
        with self._lock:
            self.rows.append(row)


def ip_for(index: int) -> str:
    n = index + 1
    return f"10.{(n >> 16) & 255}.{(n >> 8) & 255}.{n & 255}"


def call(
    target: Target,
    rec: Recorder,
    op: str,
    method: str,
    path: str,
    *,
    body: dict | None = None,
    ip: str,
    cookie: str | None = None,
    timeout: float = CLIENT_TIMEOUT_SECONDS,
) -> tuple[int, bytes, http.client.HTTPResponse | None]:
    headers = {"X-Forwarded-For": ip, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    started = rec.now()
    t0 = time.monotonic()
    conn = target.connect(timeout)
    try:
        conn.request(method, path, body=data, headers=headers)
        response = conn.getresponse()
        payload = response.read()
        status = response.status
    except (OSError, http.client.HTTPException) as exc:
        rec.add(op, started, 0, time.monotonic() - t0, error=type(exc).__name__)
        return 0, b"", None
    finally:
        conn.close()
    rec.add(op, started, status, time.monotonic() - t0)
    return status, payload, response


def session_cookie(response: http.client.HTTPResponse | None) -> str | None:
    if response is None:
        return None
    for header in response.headers.get_all("Set-Cookie") or []:
        return header.split(";", 1)[0]
    return None


def spread(count: int, over: float, work) -> list[threading.Thread]:
    """Start ``work(i)`` for each person at an even pace over ``over`` seconds."""
    threads = []
    begin = time.monotonic()
    for i in range(count):
        delay = begin + (over * i / count if count else 0) - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        thread = threading.Thread(target=work, args=(i,), daemon=True)
        thread.start()
        threads.append(thread)
    return threads


def join(threads: list[threading.Thread]) -> None:
    for thread in threads:
        thread.join()


class ReadyProbe(threading.Thread):
    """Asks ``/api/health/ready`` every half second for the whole test."""

    def __init__(self, target: Target, rec: Recorder) -> None:
        super().__init__(daemon=True)
        self.target, self.rec = target, rec
        self.stop = threading.Event()

    def run(self) -> None:
        while not self.stop.is_set():
            call(
                self.target,
                self.rec,
                "ready",
                "GET",
                "/api/health/ready",
                ip="127.0.0.1",
                timeout=30,
            )
            self.stop.wait(0.5)


class DbSampler(threading.Thread):
    """Every second: the server's connections to the database, by state."""

    QUERY = """
        SELECT state, count(*),
               coalesce(max(extract(epoch FROM now() - state_change)), 0)
        FROM pg_stat_activity
        WHERE datname = current_database() AND pid <> pg_backend_pid()
        GROUP BY state
    """

    def __init__(self, db_url: str, rec: Recorder) -> None:
        super().__init__(daemon=True)
        import psycopg2

        self.conn = psycopg2.connect(db_url)
        self.conn.autocommit = True
        self.rec = rec
        self.samples: list[dict] = []
        self.stop = threading.Event()

    def sample(self) -> dict:
        with self.conn.cursor() as cur:
            cur.execute(self.QUERY)
            rows = cur.fetchall()
        sample = {"t": round(self.rec.now(), 1), "total": 0}
        for state, count, oldest in rows:
            sample[state or "none"] = count
            sample["total"] += count
            if state == "idle in transaction":
                sample["idle_in_tx_oldest_s"] = round(float(oldest), 1)
        return sample

    def scalar(self, sql: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]

    def run(self) -> None:
        while not self.stop.is_set():
            self.samples.append(self.sample())
            self.stop.wait(1)


# --- what one person does ---------------------------------------------------------


def login(target, rec, i, *, ip=None, op="login") -> str | None:
    status, _, response = call(
        target,
        rec,
        op,
        "POST",
        "/api/auth/login",
        body={"email": EMAIL_PATTERN.format(i), "password": PASSWORD},
        ip=ip or ip_for(i),
    )
    return session_cookie(response) if status == 200 else None


def initiate(target, rec, i, cookie) -> str | None:
    status, payload, _ = call(
        target,
        rec,
        "initiate",
        "POST",
        "/api/payment/initiate",
        body={"ticket_tier": "geral", "phone": PHONE},
        ip=ip_for(i),
        cookie=cookie,
    )
    if status != 201:
        return None
    return json.loads(payload)["reference"]


def follow(target, rec, i, cookie, reference, *, hold=None, timeout=300.0):
    """Open the live status stream and read it until the payment is decided (or for
    ``hold`` seconds). Records how long the first byte took and the final status."""
    path = f"/api/payment/transactions/{reference}/events"
    started = rec.now()
    t0 = time.monotonic()
    conn = target.connect(timeout=30)
    final, events, first_ms = None, 0, None
    try:
        conn.request(
            "GET",
            path,
            headers={
                "X-Forwarded-For": ip_for(i),
                "Cookie": cookie,
                "Accept": "text/event-stream",
            },
        )
        response = conn.getresponse()
        first_ms = round((time.monotonic() - t0) * 1000, 1)
        if response.status != 200:
            response.read()
            rec.add("sse", started, response.status, time.monotonic() - t0)
            return None
        limit = time.monotonic() + (hold if hold is not None else timeout)
        while time.monotonic() < limit:
            line = response.readline()
            if not line:
                break
            events += 1
            if line.startswith(b"data:"):
                status = json.loads(line[5:]).get("status")
                if status in FINAL_STATUSES:
                    final = status
                    break
    except (OSError, http.client.HTTPException, ValueError) as exc:
        rec.add(
            "sse",
            started,
            0,
            time.monotonic() - t0,
            error=type(exc).__name__,
            first_ms=first_ms,
            lines=events,
        )
        return None
    finally:
        conn.close()
    rec.add(
        "sse",
        started,
        200,
        time.monotonic() - t0,
        first_ms=first_ms,
        lines=events,
        final=final,
    )
    return final


def sign_in_all(target, rec, count, offset=0) -> dict[int, str]:
    """Sign everyone in before the measured part (not counted in the results)."""
    cookies: dict[int, str] = {}

    def work(i):
        cookie = login(target, rec, offset + i, op="setup-login")
        if cookie:
            cookies[offset + i] = cookie

    join(spread(count, min(10.0, count / 30), work))
    missing = count - len(cookies)
    if missing:
        print(f"warning: {missing} people could not sign in", file=sys.stderr)
    return cookies


# --- scenarios --------------------------------------------------------------------


def scenario_login(target, rec, args):
    join(spread(args.users, args.over, lambda i: login(target, rec, i)))


def scenario_campus(target, rec, args):
    """Everyone behind the same address opens the shop page and signs in."""

    def person(i):
        call(target, rec, "tiers", "GET", "/api/payment/tiers", ip=CAMPUS_IP)
        login(target, rec, i, ip=CAMPUS_IP)

    join(spread(args.users, args.over, person))


def buy(target, rec, i, cookie, args):
    reference = initiate(target, rec, i, cookie)
    if reference:
        follow(target, rec, i, cookie, reference, timeout=args.follow_timeout)


def scenario_payments(target, rec, args):
    cookies = sign_in_all(target, rec, args.users)
    rec.measure_from = rec.now()
    join(
        spread(
            args.users,
            args.over,
            lambda i: cookies.get(i) and buy(target, rec, i, cookies[i], args),
        )
    )


def scenario_sse(target, rec, args):
    cookies = sign_in_all(target, rec, args.users)
    references = {}

    def start(i):
        if i in cookies:
            references[i] = initiate(target, rec, i, cookies[i])

    join(spread(args.users, min(30.0, args.users / 10), start))
    rec.measure_from = rec.now()
    join(
        spread(
            args.users,
            args.over,
            lambda i: (
                references.get(i)
                and follow(
                    target,
                    rec,
                    i,
                    cookies[i],
                    references[i],
                    hold=args.hold,
                    timeout=args.follow_timeout,
                )
            ),
        )
    )


def register(target, rec, i, run_id):
    call(
        target,
        rec,
        "register",
        "POST",
        "/api/auth/register",
        body={
            "name": "Pessoa Carga",
            "email": f"reg-{run_id}-{i:04d}@loadtest.example.com",
            "password": PASSWORD,
            "accept_terms": True,
        },
        ip=ip_for(100_000 + i),
    )


def scenario_register(target, rec, args):
    run_id = int(time.time())
    join(spread(args.users, args.over, lambda i: register(target, rec, i, run_id)))


def scenario_mix(target, rec, args):
    n = args.users
    cookies = sign_in_all(target, rec, n)
    run_id = int(time.time())
    rec.measure_from = rec.now()
    stop = threading.Event()

    def read_tiers():
        k = 0
        while not stop.is_set():
            call(
                target,
                rec,
                "tiers",
                "GET",
                "/api/payment/tiers",
                ip=ip_for(200_000 + k % 1000),
            )
            k += 1
            stop.wait(0.2)

    reader = threading.Thread(target=read_tiers, daemon=True)
    reader.start()
    groups = [
        spread_async(
            n,
            args.over,
            lambda i: cookies.get(i) and buy(target, rec, i, cookies[i], args),
        ),
        spread_async(n, args.over, lambda i: login(target, rec, n + i)),
        spread_async(
            n if args.sign_ups is None else args.sign_ups,
            args.over,
            lambda i: register(target, rec, i, run_id),
        ),
    ]
    for group in groups:
        group.join()
    stop.set()
    reader.join()


def spread_async(count, over, work) -> threading.Thread:
    runner = threading.Thread(
        target=lambda: join(spread(count, over, work)), daemon=True
    )
    runner.start()
    return runner


SCENARIOS = {
    "login": scenario_login,
    "campus": scenario_campus,
    "payments": scenario_payments,
    "sse": scenario_sse,
    "register": scenario_register,
    "mix": scenario_mix,
}


# --- after the test ---------------------------------------------------------------


def wait_until_settled(sampler: DbSampler, rec: Recorder, timeout: float) -> dict:
    """Wait for every payment to be decided and the email queue to be empty."""
    deadline = time.monotonic() + timeout
    while True:
        pending = sampler.scalar(
            "SELECT count(*) FROM transactions WHERE status = 'pending'"
        )
        outbox = sampler.scalar(
            "SELECT count(*) FROM email_outbox WHERE status = 'pending'"
        )
        if (pending == 0 and outbox == 0) or time.monotonic() > deadline:
            break
        time.sleep(1)
    drain = sampler.scalar(
        "SELECT coalesce(extract(epoch FROM max(sent_at) - min(created_at)), 0)"
        "::int FROM email_outbox WHERE status = 'sent'"
    )
    return {
        "settled_at_s": round(rec.now(), 1),
        "payments_pending": pending,
        "payments_by_status": dict(
            Counter(
                dict(
                    sampler_rows(
                        sampler,
                        "SELECT status, count(*) FROM transactions GROUP BY status",
                    )
                )
            )
        ),
        "tickets": sampler.scalar("SELECT count(*) FROM tickets"),
        "emails_pending": outbox,
        "emails_sent": sampler.scalar(
            "SELECT count(*) FROM email_outbox WHERE status = 'sent'"
        ),
        "emails_drain_s": drain,
    }


def sampler_rows(sampler: DbSampler, sql: str) -> list[tuple]:
    with sampler.conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p / 100 * len(ordered)) - 1))
    return ordered[index]


def summarize(rows: list[dict], measure_from: float) -> dict:
    summary = {}
    measured = [r for r in rows if r["t"] >= measure_from or r["op"] == "ready"]
    for op in sorted({r["op"] for r in measured}):
        ops = [r for r in measured if r["op"] == op]
        ms = [r["ms"] for r in ops]
        statuses = Counter(str(r["status"]) for r in ops)
        entry = {
            "count": len(ops),
            "status": dict(statuses),
            "p50_ms": round(statistics.median(ms), 1),
            "p95_ms": pct(ms, 95),
            "p99_ms": pct(ms, 99),
            "max_ms": max(ms),
            "5xx_or_no_answer": sum(
                1 for r in ops if r["status"] >= 500 or r["status"] == 0
            ),
        }
        if op == "sse":
            firsts = [r["first_ms"] for r in ops if r.get("first_ms") is not None]
            entry["first_byte_p95_ms"] = pct(firsts, 95)
            entry["final"] = dict(Counter(str(r.get("final")) for r in ops))
        summary[op] = entry
    return summary


def server_log_errors(path: Path | None) -> dict | None:
    """Pool timeouts and unhandled errors in the server's log, if we have it."""
    if path is None:
        return None
    text = path.read_text(errors="replace")
    return {
        "pool_timeouts": text.count("QueuePool limit"),
        "tracebacks": text.count("Traceback"),
    }


def criteria(summary: dict, db: dict | None, log: dict | None) -> dict:
    requests = [v for k, v in summary.items() if k != "ready"]
    total = sum(v["count"] for v in requests)
    errors = sum(v["5xx_or_no_answer"] for v in requests)
    ready = summary.get("ready", {})
    result = {
        "5xx_rate_below_1pct": total == 0 or errors / total < 0.01,
        "ready_always_below_1s": ready.get("max_ms", 0) < READY_SLOW_SECONDS * 1000
        and ready.get("5xx_or_no_answer", 0) == 0,
    }
    if db is not None:
        result["no_stuck_connection"] = db["idle_in_tx_at_end"] == 0
        result["all_payments_resolved"] = db["settle"]["payments_pending"] == 0
    if log is not None:
        # The pool is exhausted when a request waits DB_POOL_TIMEOUT for a connection
        # and gives up; using all of it (one per server thread) is not.
        result["pool_never_exhausted"] = log["pool_timeouts"] == 0
        result["no_unhandled_error"] = log["tracebacks"] == 0
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("\n\n", 3)[3],
    )
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--remote", action="store_true", help="allow a --base that is not this machine"
    )
    parser.add_argument("--users", type=int, default=300)
    parser.add_argument(
        "--over", type=float, default=10.0, help="seconds over which the people arrive"
    )
    parser.add_argument(
        "--hold",
        type=float,
        help="sse: seconds each stream stays open (by default, until decided)",
    )
    parser.add_argument(
        "--sign-ups", type=int, help="mix: new accounts (by default, --users)"
    )
    parser.add_argument("--follow-timeout", type=float, default=300.0)
    parser.add_argument("--settle-timeout", type=float, default=300.0)
    parser.add_argument("--db-url", help="postgresql://... of the load-test database")
    parser.add_argument(
        "--pool-limit",
        type=int,
        default=40,
        help="DB_POOL_SIZE + DB_MAX_OVERFLOW of the server",
    )
    parser.add_argument(
        "--server-log", type=Path, help="the server's log, checked for pool timeouts"
    )
    parser.add_argument("--label", default="")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    target = Target(args.base)
    if not target.is_local and not args.remote:
        raise SystemExit(
            f"{args.base} is not this machine: pass --remote if that is intended "
            "(never against production)"
        )

    rec = Recorder()
    rec.measure_from = 0.0
    sampler = DbSampler(args.db_url, rec) if args.db_url else None
    probe = ReadyProbe(target, rec)
    probe.start()
    if sampler:
        sampler.start()

    SCENARIOS[args.scenario](target, rec, args)
    load_ended = rec.now()

    db = None
    if sampler:
        settle = wait_until_settled(sampler, rec, args.settle_timeout)
        time.sleep(2)
        sampler.stop.set()
        sampler.join()
        end = sampler.sample()
        samples = sampler.samples
        db = {
            "max_connections": max(s["total"] for s in samples),
            "pool_limit": args.pool_limit,
            "max_active": max(s.get("active", 0) for s in samples),
            "max_idle_in_tx": max(s.get("idle in transaction", 0) for s in samples),
            "max_idle_in_tx_age_s": max(
                s.get("idle_in_tx_oldest_s", 0) for s in samples
            ),
            "idle_in_tx_at_end": end.get("idle in transaction", 0),
            "settle": settle,
        }
    probe.stop.set()
    probe.join()

    summary = summarize(rec.rows, rec.measure_from)
    log = server_log_errors(args.server_log)
    result = {
        "scenario": args.scenario,
        "label": args.label,
        "users": args.users,
        "over_s": args.over,
        "load_window_s": [round(rec.measure_from, 1), round(load_ended, 1)],
        "summary": summary,
        "db": db,
        "server_log": log,
        "criteria": criteria(summary, db, log),
        "requests": rec.rows,
        "db_samples": sampler.samples if sampler else [],
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1))

    printable = {k: v for k, v in result.items() if k not in {"requests", "db_samples"}}
    print(json.dumps(printable, indent=2))
    return 0 if all(result["criteria"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
