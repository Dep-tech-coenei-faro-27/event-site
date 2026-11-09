"""Open the ticket office and set the price of a ticket modality.

Usage:
    python -m app.domains.payments.set_price geral 3500
    python -m app.domains.payments.set_price acesso 2500
    python -m app.domains.payments.set_price acesso 838 --normal 1345    # early bird
    python -m app.domains.payments.set_price --show                      # read only

``--normal`` is the regular price, shown struck through next to the price while an
early-bird price is in force. Setting a price without ``--normal`` clears it, so the
change from early bird to the regular price is ``set_price acesso 1345``.

The early bird ends by itself (``EARLY_BIRD_ENDS_AT``, ``EARLY_BIRD_TICKET_LIMIT``) but
only for a modality that has its ``--normal`` price saved: at the end the regular price
is written as the price (and ``--normal`` is cleared), for good, with no command.
``--show`` prints every modality (price saved, regular price saved, price in force
now) and warns about the ones that would NOT change by themselves; it changes nothing.
Setting a price without ``--normal`` erases the saved regular price, so after a test
price always set the early-bird price back with it.

The price (with VAT, in cents) must be greater than zero; a NULL price means
the ticket office is closed and ``/payment/initiate`` answers 503. There is no stock
per modality: the seats for sale are one number for all of them, ``TICKET_STOCK_LIMIT``.
"""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.domains.payments.models import TicketTier, TicketTierPrice
from app.domains.payments.service import (
    early_bird_is_over,
    early_bird_places_taken,
    price_in_force,
)
from app.domains.payments.tiers import TIER_SPECS


def set_price(
    db: Session,
    tier: TicketTier,
    price_cents: int,
    normal_price_cents: int | None = None,
) -> TicketTierPrice:
    if price_cents <= 0:
        raise ValueError("price_cents must be greater than 0")
    if normal_price_cents is not None and normal_price_cents <= price_cents:
        raise ValueError("normal_price_cents must be greater than price_cents")

    tier_row = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == tier))
    if tier_row is None:
        spec = TIER_SPECS[tier]
        tier_row = TicketTierPrice(
            tier=tier,
            name=spec.name,
            price_cents=price_cents,
            normal_price_cents=normal_price_cents,
            is_student=spec.is_student,
        )
        db.add(tier_row)
    else:
        tier_row.price_cents = price_cents
        tier_row.normal_price_cents = normal_price_cents

    db.commit()
    db.refresh(tier_row)
    return tier_row


def _eur(cents: int | None) -> str:
    return "-" if cents is None else f"{cents / 100:.2f}"


def describe_prices(db: Session) -> tuple[list[str], int]:
    """The prices as they stand, line by line, and how many need attention."""
    over = early_bird_is_over(db)
    ends = settings.EARLY_BIRD_ENDS_AT
    lines = [
        f"Early bird: {'OVER' if over else 'in force'}; ends "
        + (f"on {ends:%Y-%m-%d %H:%M} UTC or " if ends else "")
        + f"when {settings.EARLY_BIRD_TICKET_LIMIT} places are taken "
        f"({early_bird_places_taken(db)} now)"
    ]
    order = {tier: index for index, tier in enumerate(TicketTier)}
    rows = sorted(db.scalars(select(TicketTierPrice)), key=lambda r: order[r.tier])
    present = {row.tier for row in rows}
    problems = 0
    for row in rows:
        price, struck = price_in_force(row, over)
        note = ""
        if row.price_cents is None:
            note = "CLOSED: no price"
        elif row.normal_price_cents is None and not over:
            note = (
                "!! no regular price saved: it will NOT change by itself "
                "(ignore if the early bird already ended)"
            )
            problems += 1
        lines.append(
            f"{row.tier.value:<16} saved {_eur(row.price_cents):>7}  "
            f"regular {_eur(row.normal_price_cents):>7}  "
            f"in force {_eur(price):>7}  {note}".rstrip()
        )
    for tier in TicketTier:
        if tier not in present:
            lines.append(f"{tier.value:<16} !! not created yet (no price)")
            problems += 1
    return lines, problems


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Set a ticket modality price")
    parser.add_argument("tier", nargs="?", choices=[tier.value for tier in TicketTier])
    parser.add_argument(
        "price_cents", nargs="?", type=int, help="price with VAT, in cents"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="print the prices and what is in force now; changes nothing",
    )
    parser.add_argument(
        "--normal",
        type=int,
        default=None,
        metavar="CENTS",
        help="regular price, in cents, while price_cents is an early-bird price",
    )
    args = parser.parse_args(argv)

    if args.show:
        if args.tier or args.price_cents is not None or args.normal is not None:
            parser.error("--show takes no modality, price or --normal")
        with SessionLocal() as db:
            lines, problems = describe_prices(db)
        print("\n".join(lines))
        sys.exit(1 if problems else 0)
    if args.tier is None or args.price_cents is None:
        parser.error("give a modality and a price in cents (or --show)")

    try:
        with SessionLocal() as db:
            ticket = set_price(db, TicketTier(args.tier), args.price_cents, args.normal)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"{ticket.tier.value}: price_cents={ticket.price_cents}"
        f" normal_price_cents={ticket.normal_price_cents}"
    )


if __name__ == "__main__":
    main()
