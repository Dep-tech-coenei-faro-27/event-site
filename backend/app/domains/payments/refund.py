"""Give a payment back through the provider's API.

    python -m app.domains.payments.refund ENEI-0123456789
    python -m app.domains.payments.refund --due

The first form refunds one payment: a ``refund_due`` (it arrived and there is no
ticket to give) or a ``confirmed`` one, whose ticket is cancelled and its seat freed.
``--due`` goes through every ``refund_due`` in turn. Repeating a command is safe: a
payment that is already ``refunded`` is left alone and the provider never refunds the
same payment twice. Only the reference and the amount are printed.
"""

import argparse
import sys

from fastapi import HTTPException

from app.db.session import SessionLocal
from app.domains.payments.gateway import PaymentGatewayError, get_mbway_gateway
from app.domains.payments.service import (
    PaymentError,
    refund_payment,
    refundable_references,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.domains.payments.refund")
    parser.add_argument(
        "reference", nargs="?", help="the payment, e.g. ENEI-0123456789"
    )
    parser.add_argument(
        "--due", action="store_true", help="refund every payment waiting for it"
    )
    args = parser.parse_args(argv)
    if bool(args.reference) == args.due:
        parser.error("give a payment reference, or --due")

    try:
        gateway = get_mbway_gateway()
    except HTTPException:
        print("Payments are off (PAYMENTS_MODE=off): nothing to refund with.")
        return 1

    failed = 0
    with SessionLocal() as db:
        references = refundable_references(db) if args.due else [args.reference]
        if not references:
            print("Nothing waiting for a refund.")
        for reference in references:
            try:
                transaction = refund_payment(db, reference, gateway)
            except (PaymentError, PaymentGatewayError) as error:
                db.rollback()
                failed += 1
                print(f"{reference}: NOT refunded: {error}")
                continue
            print(
                f"{reference}: {transaction.status.value} "
                f"({transaction.amount_cents / 100:.2f} EUR)"
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
