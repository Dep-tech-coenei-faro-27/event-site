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


def test_set_price_with_a_normal_price_marks_an_early_bird(db_session):
    set_price(db_session, TicketTier.ACESSO, 838, 1345)

    row = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.ACESSO)
    )
    assert row is not None
    assert (row.price_cents, row.normal_price_cents) == (838, 1345)


def test_set_price_without_a_normal_price_ends_the_early_bird(db_session):
    set_price(db_session, TicketTier.ACESSO, 838, 1345)

    set_price(db_session, TicketTier.ACESSO, 1345)

    row = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.ACESSO)
    )
    assert row is not None
    assert (row.price_cents, row.normal_price_cents) == (1345, None)


@pytest.mark.parametrize("normal", [838, 500])
def test_set_price_rejects_a_normal_price_that_is_not_above_the_price(
    db_session, normal
):
    with pytest.raises(ValueError):
        set_price(db_session, TicketTier.ACESSO, 838, normal)
