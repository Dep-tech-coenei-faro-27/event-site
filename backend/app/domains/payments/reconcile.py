"""Compare, read only, what Stripe received with what the site counted as sold.

    python -m app.domains.payments.reconcile                 # what does not match
    python -m app.domains.payments.reconcile --list site     # every site payment
    python -m app.domains.payments.reconcile --list stripe   # every Stripe payment
    python -m app.domains.payments.reconcile --list side     # both, side by side
    python -m app.domains.payments.reconcile --list all --csv vendas.csv

``--list`` chooses what is printed (and written with ``--csv``):

* ``compare`` (default): the totals of each side and only the payments that do not
  match, plus the ones that need a hand (partial refunds, refunds waiting);
* ``site``: every payment recorded by the site, in any state;
* ``stripe``: every PaymentIntent recorded by Stripe, in any state;
* ``side``: every payment on both sides in one table, one row each, with the result;
* ``all``: like ``side``, with the PaymentIntent id and the dates as well.

``--since 2026-11-09`` limits it to a day onwards, ``--paid`` leaves out the payments
that never completed, ``--fees`` adds Stripe's fee and net, and ``--with-nif`` adds the
tax number the buyer gave (for the invoices: it is personal data, so it is off unless
asked for).

It pairs the two sides by the PaymentIntent id (or by the ``ENEI-…`` reference Stripe
keeps in the metadata) and calls these a problem:

* money Stripe received that the site did not count (no ticket, no invoice);
* a payment the site counts that Stripe never received;
* a different amount on each side;
* a refund done in the Stripe dashboard while the ticket is still valid (a partial
  refund is only listed, because the ticket is then cancelled by hand);
* a Stripe payment the site does not know at all.
* a payment the customer's bank disputed (a chargeback), which the site never hears of;
* a refund done at Stripe while the site still says ``refund_due``.

Nothing is changed, at Stripe or in the database, and no name, email or phone is ever
printed or written: references, ids, amounts, dates and, only with ``--with-nif``,
the NIF. Exit code 1 if anything does not match (for ``compare`` and ``side``/``all``
alike), so it can also run on a schedule.

The key needs to read PaymentIntents and Charges (``--fees`` also Balance
transactions). With a restricted ``rk_live_`` key that is "read" on those.
"""

import argparse
import csv
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.domains.payments.gateway import PaymentGatewayError, StripeMBWayGateway
from app.domains.payments.models import (
    TicketTierPrice,
    Transaction,
    TransactionStatus,
)

# What the site counts as money that arrived: a ticket given, a payment waiting to be
# paid back (it arrived but there is no ticket) and a ticket paid back.
COUNTED = {
    TransactionStatus.CONFIRMED,
    TransactionStatus.REFUND_DUE,
    TransactionStatus.REFUNDED,
}
COUNTED_VALUES = {status.value for status in COUNTED}

PAGE = 100
# The Stripe account is shared with other events and products: ours are the payments
# whose metadata carries one of our references.
OUR_REFERENCE_PREFIX = "ENEI-"
# A mismatch on a payment this young is probably just the webhook still on its way:
# it is shown, but as information and not as a problem.
GRACE_SECONDS = 900
LISTINGS = ("compare", "site", "stripe", "side", "all")

# The columns of each listing, in order: (attribute of Row, heading).
SITE_COLUMNS = [
    ("reference", "reference"),
    ("site_tier", "tier"),
    ("site_status", "site_status"),
    ("site_amount_cents", "site_amount_cents"),
    ("site_created", "site_created"),
    ("site_confirmed_at", "site_confirmed_at"),
]
STRIPE_COLUMNS = [
    ("payment_intent", "payment_intent"),
    ("reference", "reference"),
    ("stripe_status", "stripe_status"),
    ("stripe_amount_cents", "stripe_amount_cents"),
    ("stripe_refunded_cents", "stripe_refunded_cents"),
    ("stripe_created", "stripe_created"),
]
FEE_COLUMNS = [
    ("stripe_fee_cents", "stripe_fee_cents"),
    ("stripe_net_cents", "stripe_net_cents"),
]
SIDE_COLUMNS = [
    ("reference", "reference"),
    ("site_status", "site_status"),
    ("site_amount_cents", "site_amount_cents"),
    ("stripe_status", "stripe_status"),
    ("stripe_amount_cents", "stripe_amount_cents"),
    ("stripe_refunded_cents", "stripe_refunded_cents"),
    ("result", "result"),
    ("note", "note"),
]
ALL_COLUMNS = [
    ("reference", "reference"),
    ("payment_intent", "payment_intent"),
    ("site_tier", "tier"),
    ("site_status", "site_status"),
    ("site_amount_cents", "site_amount_cents"),
    ("site_created", "site_created"),
    ("site_confirmed_at", "site_confirmed_at"),
    ("stripe_status", "stripe_status"),
    ("stripe_amount_cents", "stripe_amount_cents"),
    ("stripe_refunded_cents", "stripe_refunded_cents"),
    ("stripe_created", "stripe_created"),
    ("result", "result"),
    ("note", "note"),
]
NIF_COLUMN = [("nif", "nif")]


@dataclass
class Row:
    """One payment, as Stripe and the site see it. Either side may be missing."""

    result: str = "ok"  # ok | info | PROBLEM
    note: str = ""
    reference: str = ""
    payment_intent: str = ""
    stripe_status: str = ""
    stripe_amount_cents: int | None = None
    stripe_refunded_cents: int = 0
    stripe_fee_cents: int | None = None
    stripe_net_cents: int | None = None
    stripe_created: str = ""
    site_tier: str = ""
    site_status: str = ""
    site_amount_cents: int | None = None
    site_created: str = ""
    site_confirmed_at: str = ""
    nif: str = ""
    # Not a sale on either side: a checkout someone left (Stripe) or a payment that
    # never reached Stripe (site). Kept for the listings, left out of the comparison.
    unfinished: bool = False
    # A payment of another product of the same Stripe account (it has no ``ENEI-…``
    # reference and the site never heard of it): not ours, so never compared.
    other: bool = False
    # Seconds since the payment was made (Stripe's clock, or the site's for a payment
    # Stripe does not have).
    age_seconds: int | None = None
    # The customer's bank disputed the payment (a chargeback). The site does not know
    # about it: nothing handles ``charge.dispute.*``.
    disputed: bool = False

    @property
    def paid_at_stripe(self) -> bool:
        return self.stripe_status == "succeeded" and not self.other

    @property
    def counted_by_site(self) -> bool:
        return self.site_status in COUNTED_VALUES


@dataclass
class Report:
    rows: list[Row] = field(default_factory=list)

    @property
    def problems(self) -> list[Row]:
        return [row for row in self.rows if row.result == "PROBLEM"]

    @property
    def infos(self) -> list[Row]:
        return [row for row in self.rows if row.result == "info"]

    @property
    def sales(self) -> list[Row]:
        """The rows that are a sale on at least one side."""
        return [row for row in self.rows if not (row.unfinished or row.other)]

    @property
    def others(self) -> list[Row]:
        """Payments of other products of the Stripe account."""
        return [row for row in self.rows if row.other]


def _iso(timestamp: object) -> str:
    if type(timestamp) is not int:
        return ""
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d %H:%M")


def _stamp(moment: datetime | None) -> str:
    return f"{moment:%Y-%m-%d %H:%M}" if moment else ""


def _eur(cents: int | None) -> str:
    return "?" if cents is None else f"{cents / 100:.2f} EUR"


def _clean(value: object, *, limit: int = 40) -> str:
    """Text that came from Stripe, safe to print and to put in a spreadsheet.

    The reference lives in the metadata of the payment, and the account is shared with
    other products whose metadata is not ours: only letters, digits and ``_ . : -``
    are kept, so a control character cannot reach the terminal and a cell cannot
    start with ``=`` and run as a formula.
    """
    return re.sub(r"[^A-Za-z0-9_.:-]", "", str(value or ""))[:limit]


def _charge(intent: dict) -> dict:
    charge = intent.get("latest_charge")
    return charge if isinstance(charge, dict) else {}


def _stripe_side(intent: dict, now: datetime) -> Row:
    charge = _charge(intent)
    balance = charge.get("balance_transaction")
    balance = balance if isinstance(balance, dict) else {}
    received = intent.get("amount_received")
    refunded = charge.get("amount_refunded")
    created = intent.get("created")
    return Row(
        age_seconds=int(now.timestamp() - created) if type(created) is int else None,
        reference=_clean((intent.get("metadata") or {}).get("reference")),
        payment_intent=_clean(intent.get("id")),
        stripe_status=_clean(intent.get("status")),
        disputed=charge.get("disputed") is True,
        stripe_amount_cents=received if type(received) is int else None,
        stripe_refunded_cents=refunded if type(refunded) is int else 0,
        stripe_fee_cents=balance.get("fee"),
        stripe_net_cents=balance.get("net"),
        stripe_created=_iso(intent.get("created")),
    )


def _site_side(row: Row, site: Transaction, tiers: dict[int, str]) -> None:
    row.reference = site.reference
    row.payment_intent = row.payment_intent or site.provider_reference or ""
    row.site_tier = tiers.get(site.ticket_tier_id, "")
    row.site_status = site.status.value
    row.site_amount_cents = site.amount_cents
    row.site_created = _stamp(site.created_at)
    row.site_confirmed_at = _stamp(site.confirmed_at)
    row.nif = site.nif or ""


def _judge(row: Row, site: Transaction | None) -> None:
    """Set ``result`` and ``note`` of a row that has a Stripe side."""
    paid = row.paid_at_stripe
    if site is None and not row.reference.startswith(OUR_REFERENCE_PREFIX):
        row.other, row.result = True, "other"
        row.note = "a payment of another product of the account, not compared"
        return
    if site is None:
        if paid:
            row.result, row.note = (
                "PROBLEM",
                "Stripe received this money and the site has no such payment",
            )
        else:
            row.unfinished = True
        return

    counted = row.counted_by_site
    if paid and not counted:
        row.result, row.note = (
            "PROBLEM",
            f"Stripe received the money but the site says {row.site_status}: "
            "no ticket and no invoice",
        )
    elif counted and not paid:
        row.result, row.note = (
            "PROBLEM",
            f"the site counts it as {row.site_status} but Stripe did not receive it",
        )
    elif paid and row.stripe_amount_cents != row.site_amount_cents:
        row.result, row.note = (
            "PROBLEM",
            f"Stripe received {_eur(row.stripe_amount_cents)} and the site "
            f"charged {_eur(row.site_amount_cents)}",
        )
    elif paid:
        _judge_refund(row, site)
    else:
        row.unfinished = True  # neither side counts it: a payment that did not happen


def _flag_dispute(row: Row) -> None:
    """A disputed payment is always a problem, whatever else is true of it.

    The site never hears of a dispute (the webhook does not handle them) and the money
    can be taken back by the bank: it has to be answered in the Stripe dashboard before
    its deadline, and the ticket cancelled by hand if the dispute is lost.
    """
    if row.disputed and not row.other:
        before = f" ({row.note})" if row.note else ""
        row.result = "PROBLEM"
        row.note = (
            "DISPUTED at Stripe (chargeback): answer it in the dashboard before the "
            f"deadline; the site does not know about it{before}"
        )


def _soften(row: Row) -> None:
    """A mismatch on a very recent payment is information: the webhook may be coming."""
    if (
        row.result == "PROBLEM"
        and row.age_seconds is not None
        and row.age_seconds < GRACE_SECONDS
    ):
        row.result = "info"
        row.note = f"recent, may still be catching up: {row.note}"


def _judge_refund(row: Row, site: Transaction) -> None:
    refunded = row.stripe_refunded_cents
    total = row.stripe_amount_cents
    full = refunded > 0 and refunded >= (total or 0)
    if site.status is TransactionStatus.REFUNDED and not full:
        # Expected, not a mistake: the ticket of a partial refund (or of a payment taken
        # back with no refund at all) is cancelled by hand with ``cancel_ticket``, which
        # marks it refunded without touching Stripe. Listed so it is seen.
        row.result, row.note = (
            "info",
            "ticket cancelled on the site; Stripe has refunded "
            f"{_eur(refunded)} of {_eur(total)} (a partial refund, or none)",
        )
    elif site.status is TransactionStatus.CONFIRMED and full:
        row.result, row.note = (
            "PROBLEM",
            "refunded in full at Stripe but the ticket is still valid on the site",
        )
    elif site.status is TransactionStatus.CONFIRMED and refunded:
        row.result, row.note = (
            "info",
            f"partial refund of {_eur(refunded)} at Stripe: the ticket stays "
            "valid until it is cancelled by hand (cancel_ticket)",
        )
    elif site.status is TransactionStatus.REFUND_DUE and full:
        row.result, row.note = (
            "PROBLEM",
            "already refunded at Stripe but the site still says refund_due",
        )
    elif site.status is TransactionStatus.REFUND_DUE:
        row.result, row.note = (
            "info",
            "arrived without a ticket to give: waiting to be paid back "
            "(python -m app.domains.payments.refund --due)",
        )


def reconcile(
    intents: Iterable[dict],
    transactions: Iterable[Transaction],
    tiers: dict[int, str] | None = None,
    now: datetime | None = None,
) -> Report:
    """Pair every PaymentIntent with the site's payment and judge each pair.

    Every payment of either side is a row, so the same result serves the comparison
    and the listings; ``Row.unfinished`` marks the ones that are not a sale.
    """
    tiers = tiers or {}
    now = now or datetime.now(UTC)
    by_intent: dict[str, Transaction] = {}
    by_reference: dict[str, Transaction] = {}
    for transaction in transactions:
        by_reference[transaction.reference] = transaction
        if transaction.provider_reference:
            by_intent[transaction.provider_reference] = transaction

    report = Report()
    seen: set[str] = set()
    for intent in intents:
        row = _stripe_side(intent, now)
        site = by_intent.get(row.payment_intent)
        if site is None:
            # By the reference in the metadata, unless the site already pairs that
            # payment with another PaymentIntent (then this one is a different try).
            candidate = by_reference.get(row.reference)
            if candidate and not candidate.provider_reference:
                site = candidate
        if site is not None:
            seen.add(site.reference)
            _site_side(row, site, tiers)
        _judge(row, site)
        _soften(row)
        _flag_dispute(row)
        report.rows.append(row)

    for transaction in by_reference.values():
        if transaction.reference in seen:
            continue
        row = Row()
        _site_side(row, transaction, tiers)
        if transaction.created_at:
            made = transaction.created_at
            made = made if made.tzinfo else made.replace(tzinfo=UTC)
            row.age_seconds = int((now - made).total_seconds())
        if row.counted_by_site:
            row.result = "PROBLEM"
            row.note = (
                f"the site counts it as {row.site_status} "
                "but Stripe has no such payment"
            )
        else:
            row.unfinished = True
        _soften(row)
        report.rows.append(row)
    return report


def fetch_intents(
    read: Callable[[str, dict | None], dict], *, since: datetime | None, fees: bool
) -> list[dict]:
    """Every PaymentIntent of the account (newest first), page by page."""
    params: dict = {"limit": PAGE, "expand[]": "data.latest_charge"}
    if fees:
        params["expand[]"] = "data.latest_charge.balance_transaction"
    if since:
        params["created[gte]"] = int(since.timestamp())
    intents: list[dict] = []
    while True:
        page = read("/payment_intents", params)
        data = [item for item in page.get("data") or [] if isinstance(item, dict)]
        intents.extend(data)
        if not page.get("has_more") or not data:
            return intents
        params = {**params, "starting_after": data[-1]["id"]}


def load_transactions(db: Session, since: datetime | None) -> list[Transaction]:
    query = select(Transaction).where(Transaction.provider == "stripe")
    if since:
        query = query.where(Transaction.created_at >= since)
    return list(db.scalars(query))


def load_tiers(db: Session) -> dict[int, str]:
    return {row.id: row.tier.value for row in db.scalars(select(TicketTierPrice))}


def totals(report: Report) -> dict[str, int]:
    stripe = [r for r in report.rows if r.paid_at_stripe]
    others = [r for r in report.others if r.stripe_status == "succeeded"]
    counted = [r for r in report.rows if r.counted_by_site]
    return {
        "stripe_paid": len(stripe),
        "stripe_cents": sum(r.stripe_amount_cents or 0 for r in stripe),
        "other_paid": len(others),
        "other_cents": sum(r.stripe_amount_cents or 0 for r in others),
        "stripe_refunded_cents": sum(r.stripe_refunded_cents for r in stripe),
        "site_counted": len(counted),
        "site_cents": sum(r.site_amount_cents or 0 for r in counted),
        "fee_known": int(any(r.stripe_fee_cents is not None for r in stripe)),
        "fee_cents": sum(r.stripe_fee_cents or 0 for r in stripe),
        "net_cents": sum(r.stripe_net_cents or 0 for r in stripe),
    }


def columns_of(listing: str, *, fees: bool, with_nif: bool) -> list[tuple[str, str]]:
    columns = {
        "site": SITE_COLUMNS,
        "stripe": STRIPE_COLUMNS + (FEE_COLUMNS if fees else []),
        "side": SIDE_COLUMNS,
        "all": ALL_COLUMNS + (FEE_COLUMNS if fees else []),
    }[listing]
    return columns + (NIF_COLUMN if with_nif and listing != "stripe" else [])


def rows_of(report: Report, listing: str, *, paid_only: bool) -> list[Row]:
    """The rows a listing shows, oldest first."""
    if listing == "site":
        rows = [r for r in report.rows if r.site_status]
    elif listing == "stripe":
        rows = [r for r in report.rows if r.stripe_status]
    else:
        rows = [r for r in report.rows if not r.other]
    if paid_only:
        rows = [r for r in rows if not (r.unfinished or r.other)]
    if listing == "stripe":
        return sorted(rows, key=lambda r: (r.stripe_created, r.payment_intent))
    return sorted(rows, key=lambda r: (r.site_created or r.stripe_created, r.reference))


def print_table(columns: list[tuple[str, str]], rows: list[Row]) -> None:
    cells = [
        [
            str(getattr(r, name) if getattr(r, name) is not None else "")
            for name, _ in columns
        ]
        for r in rows
    ]
    heads = [heading for _, heading in columns]
    widths = [
        max(len(h), *(len(c[i]) for c in cells)) if cells else len(h)
        for i, h in enumerate(heads)
    ]
    for line in [heads, *cells]:
        print(
            "  ".join(value.ljust(width) for value, width in zip(line, widths)).rstrip()
        )


def print_summary(report: Report, *, fees: bool) -> None:
    t = totals(report)
    print(f"Stripe: {t['stripe_paid']} paid, {_eur(t['stripe_cents'])} received")
    print(f"        {_eur(t['stripe_refunded_cents'])} refunded")
    if fees and not t["fee_known"]:
        print(
            "        fees: Stripe gave none (the key may not read balance transactions)"
        )
    elif fees:
        print(
            f"        fees {_eur(t['fee_cents'])}, net {_eur(t['net_cents'])} "
            "(net is before the refunds)"
        )
    print(f"Site:   {t['site_counted']} counted, {_eur(t['site_cents'])}")
    if t["other_paid"]:
        print(
            f"Not compared: {t['other_paid']} payment(s) of other products of the "
            f"Stripe account ({_eur(t['other_cents'])}); see --list stripe"
        )


def print_problems(report: Report) -> None:
    for row in report.problems + report.infos:
        mark = "!!" if row.result == "PROBLEM" else "  "
        who = row.reference or row.payment_intent or "?"
        print(f"{mark} {who}: {row.note}")
    n = len(report.problems)
    print(f"\n{n} problem(s)." if n else "\nEvery sale is counted on both sides.")


def write_csv(columns: list[tuple[str, str]], rows: list[Row], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([heading for _, heading in columns])
        for row in rows:
            writer.writerow([getattr(row, name) for name, _ in columns])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.domains.payments.reconcile")
    parser.add_argument(
        "--list",
        dest="listing",
        choices=LISTINGS,
        default="compare",
        help="what to print: compare (default), site, stripe, side or all",
    )
    parser.add_argument(
        "--since", help="only from this day on (YYYY-MM-DD, UTC); default: everything"
    )
    parser.add_argument("--csv", help="also write the listing to this file")
    parser.add_argument(
        "--paid", action="store_true", help="leave out payments that never completed"
    )
    parser.add_argument(
        "--fees", action="store_true", help="also read Stripe's fee and the net"
    )
    parser.add_argument(
        "--with-nif",
        action="store_true",
        help="add the buyer's NIF (personal data: only when you need it)",
    )
    args = parser.parse_args(argv)
    since = None
    if args.since:
        try:
            since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            parser.error("--since must be a day like 2026-11-09")

    gateway = StripeMBWayGateway(
        secret_key=settings.STRIPE_SECRET_KEY,
        timeout_seconds=settings.MBWAY_TIMEOUT_SECONDS,
        api_version=settings.STRIPE_API_VERSION,
    )
    try:
        intents = fetch_intents(gateway.read, since=since, fees=args.fees)
    except PaymentGatewayError as exc:
        key = settings.STRIPE_SECRET_KEY
        print(f"Cannot read Stripe: {str(exc).replace(key, '<key>') if key else exc}")
        print("A restricted key needs read on PaymentIntents and Charges.")
        return 2
    with SessionLocal() as db:
        transactions = load_transactions(db, since)
        tiers = load_tiers(db)
    report = reconcile(intents, transactions, tiers)

    print_summary(report, fees=args.fees)
    print()
    if args.listing == "compare":
        print_problems(report)
        rows = rows_of(report, "all", paid_only=True)
        columns = columns_of("all", fees=args.fees, with_nif=args.with_nif)
    else:
        columns = columns_of(args.listing, fees=args.fees, with_nif=args.with_nif)
        rows = rows_of(report, args.listing, paid_only=args.paid)
        print_table(columns, rows)
        print(f"\n{len(rows)} row(s), {len(report.problems)} problem(s).")
    if args.csv:
        write_csv(columns, rows, args.csv)
        print(f"Written to {args.csv}.")
    return 1 if report.problems else 0


if __name__ == "__main__":
    sys.exit(main())
