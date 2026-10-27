# ruff: noqa: F811  (the pipeline fixtures are imported from the e2e tests)
"""GET /api/users/me tells the account page about the ticket and the purchase."""

from sqlalchemy import select

from app.domains.payments.models import TicketTierPrice, TransactionStatus
from app.domains.tickets.models import PaymentStatus, Ticket
from tests.test_payment_pipeline import world  # noqa: F401

ME = "/api/users/me"


def test_a_person_who_never_bought_has_nothing(world):
    world.seed()
    ana = world.user("ana")

    body = ana.get(ME).json()

    assert body["qr_code"] is None
    assert body["ticket"] is None
    assert body["pending_payment"] is None
    assert body["refund_due"] is None


def test_a_waiting_payment_is_offered_so_the_page_can_resume_it(world):
    world.seed()
    ana = world.user("ana")
    started = world.buy(ana).json()

    body = ana.get(ME).json()

    assert body["pending_payment"] == {
        "reference": started["reference"],
        "tier": "geral",
        "tier_name": "Passe geral",
        "amount_cents": 5000,
        "expires_at": body["pending_payment"]["expires_at"],
    }
    assert body["pending_payment"]["expires_at"].startswith(started["expires_at"][:19])
    assert body["ticket"] is None and body["qr_code"] is None


def test_a_waiting_payment_stays_after_its_deadline_until_the_provider_ends_it(world):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana).json()["reference"]
    world.age(reference, minutes=30)

    assert ana.get(ME).json()["pending_payment"]["reference"] == reference

    world.provider.set_status(reference, TransactionStatus.EXPIRED)
    world.poll(ana, reference)
    assert ana.get(ME).json()["pending_payment"] is None


def test_the_paid_ticket_has_its_modality_reference_and_holder(world):
    world.seed()
    ana = world.user("ana")
    reference = world.buy(ana, tier="geral").json()["reference"]
    world.pays(ana, reference)

    body = ana.get(ME).json()

    assert body["qr_code"]
    assert body["pending_payment"] is None
    assert body["ticket"]["reference"] == reference
    assert body["ticket"]["tier"] == "geral"
    assert body["ticket"]["tier_name"] == "Passe geral"
    assert body["ticket"]["holder_name"] == "Ana"
    assert body["ticket"]["paid_at"]


def test_a_cancelled_ticket_shows_no_ticket(world):
    world.seed()
    ana = world.user("ana")
    world.pays(ana, world.buy(ana).json()["reference"])
    with world.session() as db:
        ticket = db.scalar(select(Ticket))
        ticket.payment_status = PaymentStatus.CANCELLED
        db.commit()

    body = ana.get(ME).json()

    assert body["ticket"] is None and body["qr_code"] is None


def test_a_payment_without_a_ticket_to_refund_is_shown(world):
    world.seed(limit=1)
    ana, rui = world.user("ana"), world.user("rui")
    late = world.buy(ana).json()["reference"]
    world.provider.set_status(late, TransactionStatus.EXPIRED)
    world.poll(ana, late)
    world.pays(rui, world.buy(rui).json()["reference"])
    world.callback(ana, late)  # paid after all, but the seat went to someone else

    body = ana.get(ME).json()

    assert body["refund_due"] == {"reference": late, "amount_cents": 5000}
    assert body["ticket"] is None and body["pending_payment"] is None


def test_each_person_sees_only_their_own_purchase(world):
    world.seed()
    ana, rui = world.user("ana"), world.user("rui")
    world.buy(ana)

    assert rui.get(ME).json()["pending_payment"] is None
    assert ana.get(ME).json()["pending_payment"] is not None


def test_the_existing_fields_are_unchanged(world):
    world.seed()
    ana = world.user("ana")

    body = ana.get(ME).json()

    for field in (
        "id",
        "name",
        "email",
        "role",
        "is_verified",
        "student_verification_status",
        "qr_code",
    ):
        assert field in body
    assert body["email"] == "ana@example.com"


def test_the_modality_comes_from_the_payment_not_from_the_current_price_list(world):
    world.seed()
    ana = world.user("ana")
    world.pays(ana, world.buy(ana).json()["reference"])
    with world.session() as db:
        tier = db.scalar(select(TicketTierPrice).where(TicketTierPrice.tier == "geral"))
        tier.name = "Passe geral 2027"
        db.commit()

    assert ana.get(ME).json()["ticket"]["tier"] == "geral"
