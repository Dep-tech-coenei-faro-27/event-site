import pytest
from sqlalchemy import select

from app.domains.payments.models import TicketTier, TicketTierPrice
from app.domains.payments.set_price import set_price
from tests.helpers import seed_ticket_tiers


def test_set_price_updates_an_existing_tier(db_session):
    seed_ticket_tiers(db_session)

    ticket = set_price(db_session, TicketTier.GERAL, 7500)

    assert ticket.price_cents == 7500
    stored = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.GERAL)
    )
    assert stored is not None
    assert stored.price_cents == 7500


def test_set_price_creates_a_missing_tier(db_session):
    ticket = set_price(db_session, TicketTier.ACESSO, 2500)

    stored = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.ACESSO)
    )
    assert stored is not None
    assert stored.id == ticket.id
    assert stored.price_cents == 2500
    assert stored.is_student is True


@pytest.mark.parametrize("price", [0, -1])
def test_set_price_rejects_non_positive_prices(db_session, price):
    seed_ticket_tiers(db_session)

    with pytest.raises(ValueError):
        set_price(db_session, TicketTier.GERAL, price)


def test_set_price_creates_the_general_pass_with_meals(db_session):
    set_price(db_session, TicketTier.GERAL_REFEICOES, 6500)

    row = db_session.scalar(
        select(TicketTierPrice).where(
            TicketTierPrice.tier == TicketTier.GERAL_REFEICOES
        )
    )
    assert row is not None
    assert row.name == "Passe geral + refeições"
    assert row.price_cents == 6500
    assert row.is_student is False
