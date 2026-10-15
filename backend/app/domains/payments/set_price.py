"""Open the ticket office and set the price of a ticket modality.

Usage:
    python -m app.domains.payments.set_price geral 3500
    python -m app.domains.payments.set_price acesso 2500 --stock 150

The price (with VAT, in cents) must be greater than zero; a NULL price means
the ticket office is closed and ``/payment/initiate`` answers 503.
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
    *,
    stock: int | None = None,
) -> TicketTierPrice:
    if price_cents <= 0:
        raise ValueError("price_cents must be greater than 0")
    if stock is not None and stock < 0:
        raise ValueError("stock cannot be negative")

    tier_row = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == tier))
    if tier_row is None:
        spec = TIER_SPECS[tier]
        tier_row = TicketTierPrice(
            tier=tier,
            name=spec.name,
            price_cents=price_cents,
            is_student=spec.is_student,
            inventory_limit=stock,
        )
        db.add(tier_row)
    else:
        tier_row.price_cents = price_cents
        if stock is not None:
            tier_row.inventory_limit = stock

    db.commit()
    db.refresh(tier_row)
    return tier_row


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Set a ticket modality price")
    parser.add_argument("tier", choices=[tier.value for tier in TicketTier])
    parser.add_argument("price_cents", type=int, help="price with VAT, in cents")
    parser.add_argument("--stock", type=int, default=None, help="inventory limit")
    args = parser.parse_args(argv)

    try:
        with SessionLocal() as db:
            ticket = set_price(
                db,
                TicketTier(args.tier),
                args.price_cents,
                stock=args.stock,
            )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    stock = "unlimited" if ticket.inventory_limit is None else ticket.inventory_limit
    print(f"{ticket.tier.value}: price_cents={ticket.price_cents} stock={stock}")


if __name__ == "__main__":
    main()
