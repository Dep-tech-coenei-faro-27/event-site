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


def test_show_lists_the_prices_and_warns_about_a_modality_that_will_not_change(
    db_session,
):
    from app.domains.payments import set_price as module

    seed_ticket_tiers(db_session)
    set_price(db_session, TicketTier.GERAL, 4594, 5102)  # early bird, change saved
    set_price(db_session, TicketTier.ACESSO, 838)  # no regular price saved

    lines, problems = module.describe_prices(db_session)

    assert "Early bird: in force" in lines[0]
    geral = next(line for line in lines if line.startswith("geral "))
    assert "saved   45.94" in geral and "regular   51.02" in geral
    assert "in force   45.94" in geral and "!!" not in geral
    acesso = next(line for line in lines if line.startswith("acesso "))
    assert "will NOT change by itself" in acesso
    assert problems >= 1


def test_show_says_the_early_bird_is_over_and_stops_warning(db_session, monkeypatch):
    from datetime import UTC, datetime

    from app.core.config import settings
    from app.domains.payments import set_price as module

    seed_ticket_tiers(db_session)
    set_price(db_session, TicketTier.GERAL, 4594, 5102)
    monkeypatch.setattr(
        settings, "EARLY_BIRD_ENDS_AT", datetime(2020, 1, 1, tzinfo=UTC)
    )

    lines, problems = module.describe_prices(db_session)

    assert lines[0].startswith("Early bird: OVER")
    geral = next(line for line in lines if line.startswith("geral "))
    assert "in force   51.02" in geral
    assert problems == 0


def test_show_refuses_extra_arguments():
    from app.domains.payments import set_price as module

    with pytest.raises(SystemExit) as exc:
        module.main(["--show", "geral"])

    assert exc.value.code == 2
