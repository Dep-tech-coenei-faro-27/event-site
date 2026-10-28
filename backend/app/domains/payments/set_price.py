"""Open the ticket office and set the price of a ticket modality.

Usage:
    python -m app.domains.payments.set_price geral 3500
    python -m app.domains.payments.set_price acesso 2500

The price (with VAT, in cents) must be greater than zero; a NULL price means
the ticket office is closed and ``/payment/initiate`` answers 503. There is no stock
per modality: the seats for sale are one number for all of them, ``TICKET_STOCK_LIMIT``.
"""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domains.payments.models import TicketTier, TicketTierPrice
from app.domains.payments.tiers import TIER_SPECS


def set_price(
    db: Session,
    tier: TicketTier,
    price_cents: int,
) -> TicketTierPrice:
    if price_cents <= 0:
        raise ValueError("price_cents must be greater than 0")

    tier_row = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == tier))
    if tier_row is None:
        spec = TIER_SPECS[tier]
        tier_row = TicketTierPrice(
            tier=tier,
            name=spec.name,
            price_cents=price_cents,
            is_student=spec.is_student,
        )
        db.add(tier_row)
    else:
        tier_row.price_cents = price_cents

    db.commit()
    db.refresh(tier_row)
    return tier_row


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Set a ticket modality price")
    parser.add_argument("tier", choices=[tier.value for tier in TicketTier])
    parser.add_argument("price_cents", type=int, help="price with VAT, in cents")
    args = parser.parse_args(argv)

    try:
        with SessionLocal() as db:
            ticket = set_price(db, TicketTier(args.tier), args.price_cents)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"{ticket.tier.value}: price_cents={ticket.price_cents}")


if __name__ == "__main__":
    main()
