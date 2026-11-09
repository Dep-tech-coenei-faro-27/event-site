"""Charts and a summary table from the results of ``loadtest.py``.

    python scripts/loadtest/report.py results/*.json --charts scripts/loadtest/charts

For each result, an SVG with the latency of every request over time (one colour per
kind of request, ``/api/health/ready`` as a line) and the server's database
connections; then prints a Markdown table with the numbers. Standard library only.
"""

import argparse
import json
from html import escape
from pathlib import Path

WIDTH, HEIGHT = 900, 420
PLOT = {"left": 70, "right": 20, "top": 40, "bottom": 140}
CONN_HEIGHT = 80
COLOURS = {
    "login": "#2a78d6",
    "setup-login": "#b8c4d6",
    "initiate": "#e07b1a",
    "sse": "#7a52c7",
    "register": "#2f9e57",
    "tiers": "#8a8f98",
    "ready": "#d0312d",
}


def chart(result: dict) -> str:
    rows = result["requests"]
    samples = result.get("db_samples") or []
    t_max = max([r["t"] + r["ms"] / 1000 for r in rows] + [1])
    ms_max = max([r["ms"] for r in rows if r["op"] != "setup-login"] + [1]) * 1.05
    pw = WIDTH - PLOT["left"] - PLOT["right"]
    ph = HEIGHT - PLOT["top"] - PLOT["bottom"]

    def x(t: float) -> float:
        return PLOT["left"] + pw * t / t_max

    def y(ms: float) -> float:
        return PLOT["top"] + ph * (1 - ms / ms_max)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        'font-family="sans-serif" font-size="11">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#fff"/>',
        f'<text x="{PLOT["left"]}" y="22" font-size="14" font-weight="bold">'
        f"{escape(result['scenario'])} {escape(result.get('label') or '')} "
        f"({result['users']} pessoas em {result['over_s']:g} s)</text>",
    ]
    for i in range(6):
        ms = ms_max * i / 5
        parts.append(
            f'<line x1="{PLOT["left"]}" x2="{WIDTH - PLOT["right"]}" y1="{y(ms):.1f}" '
            f'y2="{y(ms):.1f}" stroke="#eee"/><text x="{PLOT["left"] - 6}" '
            f'y="{y(ms) + 4:.1f}" text-anchor="end">{ms / 1000:.1f} s</text>'
        )
    for i in range(11):
        t = t_max * i / 10
        parts.append(
            f'<text x="{x(t):.1f}" y="{PLOT["top"] + ph + 14}" text-anchor="middle">'
            f"{t:.0f} s</text>"
        )
    window = result.get("load_window_s")
    if window:
        parts.append(
            f'<rect x="{x(window[0]):.1f}" y="{PLOT["top"]}" '
            f'width="{max(1, x(window[1]) - x(window[0])):.1f}" height="{ph}" '
            'fill="#f6f3e8" opacity="0.6"/>'
        )
    for row in rows:
        if row["op"] == "ready":
            continue
        colour = COLOURS.get(row["op"], "#555")
        failed = row["status"] == 0 or row["status"] >= 500
        parts.append(
            f'<circle cx="{x(row["t"]):.1f}" cy="{y(row["ms"]):.1f}" r="1.8" '
            f'fill="{"#000" if failed else colour}" opacity="0.6"/>'
        )
    ready = sorted((r for r in rows if r["op"] == "ready"), key=lambda r: r["t"])
    if ready:
        points = " ".join(f"{x(r['t']):.1f},{y(r['ms']):.1f}" for r in ready)
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{COLOURS["ready"]}" '
            'stroke-width="1.5"/>'
        )
    if samples:
        top = PLOT["top"] + ph + 30
        limit = (result.get("db") or {}).get("pool_limit") or max(
            s["total"] for s in samples
        )

        def cy(n: float) -> float:
            return top + CONN_HEIGHT * (1 - n / limit)

        points = " ".join(f"{x(s['t']):.1f},{cy(s['total']):.1f}" for s in samples)
        parts.append(
            f'<line x1="{PLOT["left"]}" x2="{WIDTH - PLOT["right"]}" y1="{cy(limit)}" '
            f'y2="{cy(limit)}" stroke="#d0312d" stroke-dasharray="4 3"/>'
            f'<text x="{PLOT["left"] - 6}" y="{cy(limit) + 4}" text-anchor="end">'
            f"{limit}</text>"
            f'<text x="{PLOT["left"] - 6}" y="{cy(0) + 4}" text-anchor="end">0</text>'
            f'<polyline points="{points}" fill="none" stroke="#333"/>'
            f'<text x="{PLOT["left"]}" y="{top - 4}">ligações à base de dados '
            "(tracejado: o pool)</text>"
        )
    legend_x = PLOT["left"]
    for op in [*COLOURS, "erro"]:
        if op != "erro" and not any(r["op"] == op for r in rows):
            continue
        colour = COLOURS.get(op, "#000")
        label = "ready (linha)" if op == "ready" else op
        parts.append(
            f'<circle cx="{legend_x}" cy="{HEIGHT - 10}" r="4" fill="{colour}"/>'
            f'<text x="{legend_x + 8}" y="{HEIGHT - 6}">{label}</text>'
        )
        legend_x += 30 + 7 * len(label)
    parts.append("</svg>")
    return "\n".join(parts)


def table(results: list[dict]) -> str:
    lines = [
        "| Cenário | Pedido | N | Estados | p50 | p95 | máx. | Ready máx. | "
        "Ligações máx. | Critérios falhados |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        summary = result["summary"]
        ready = summary.get("ready", {}).get("max_ms", 0)
        conns = (result.get("db") or {}).get("max_connections", "")
        failed = ", ".join(k for k, ok in result["criteria"].items() if not ok) or "—"
        name = f"{result['scenario']} {result.get('label') or ''}".strip()
        for op, entry in summary.items():
            if op == "ready":
                continue
            states = " ".join(f"{k}×{v}" for k, v in sorted(entry["status"].items()))
            lines.append(
                f"| {name} | {op} | {entry['count']} | {states} | "
                f"{entry['p50_ms'] / 1000:.2f} s | {entry['p95_ms'] / 1000:.2f} s | "
                f"{entry['max_ms'] / 1000:.2f} s | {ready / 1000:.2f} s | {conns} | "
                f"{failed} |"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--charts", type=Path, help="folder for the SVG charts")
    args = parser.parse_args()

    results = []
    for path in args.results:
        result = json.loads(path.read_text())
        results.append(result)
        if args.charts:
            args.charts.mkdir(parents=True, exist_ok=True)
            (args.charts / f"{path.stem}.svg").write_text(chart(result))
    print(table(results))


if __name__ == "__main__":
    main()
