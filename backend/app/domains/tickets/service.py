from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tickets.models import IssuedTicket


def get_ticket_for_user(
    db: Session,
    user_id: int,
) -> IssuedTicket | None:
    statement = (
        select(IssuedTicket)
        .where(
            IssuedTicket.user_id == user_id,
        )
        .order_by(IssuedTicket.id)
        .limit(1)
    )

    return db.scalar(statement)


def user_has_ticket(
    db: Session,
    user_id: int,
) -> bool:
    return get_ticket_for_user(db, user_id) is not None
