"""The comparison between what Stripe received and what the site counted as sold."""

import csv
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.domains.payments import reconcile as rec
from app.domains.payments.models import Transaction, TransactionStatus

S = TransactionStatus


def intent(n, *, status="succeeded", amount=4594, refunded=0, reference=None, fee=None):
    return {
        "id": f"pi_{n:03d}",
        "status": status,
        "amount_received": amount if status == "succeeded" else 0,
        "created": 1_700_000_000 + n,
        "metadata": {"reference": reference if reference else f"ENEI-{n:010d}"},
        "latest_charge": {
            "amount_refunded": refunded,
            "balance_transaction": {"fee": fee, "net": amount - fee} if fee else None,
        },
    }


def tx(n, status=S.CONFIRMED, amount=4594, with_intent=True):
    return Transaction(
        reference=f"ENEI-{n:010d}",
        provider="stripe",
        ticket_tier_id=1,
        provider_reference=f"pi_{n:03d}" if with_intent else None,
        status=status,
        amount_cents=amount,
        confirmed_at=datetime(2026, 11, 9, 9, 5, tzinfo=UTC),
        created_at=datetime(2023, 11, 14, 9, n, tzinfo=UTC),
    )


def notes(report):
    return {row.reference or row.payment_intent: row.note for row in report.problems}


def test_a_sale_on_both_sides_is_fine():
    report = rec.reconcile([intent(1)], [tx(1)])

    assert report.problems == [] and report.infos == []
    assert rec.totals(report)["stripe_paid"] == rec.totals(report)["site_counted"] == 1


def test_money_at_stripe_that_the_site_did_not_count_is_a_problem():
    for status in (S.PENDING, S.FAILED, S.EXPIRED):
        report = rec.reconcile([intent(1)], [tx(1, status)])

        assert "no ticket and no invoice" in notes(report)["ENEI-0000000001"]


def test_a_sale_the_site_counts_and_stripe_never_received_is_a_problem():
    unpaid = rec.reconcile([intent(1, status="canceled")], [tx(1)])
    missing = rec.reconcile([], [tx(2)])

    assert "did not receive" in notes(unpaid)["ENEI-0000000001"]
    assert "no such payment" in notes(missing)["ENEI-0000000002"]


def test_a_different_amount_is_a_problem():
    report = rec.reconcile([intent(1, amount=100)], [tx(1, amount=4594)])

    assert "1.00 EUR" in notes(report)["ENEI-0000000001"]


def test_a_payment_at_stripe_the_site_does_not_know_is_a_problem_only_if_paid():
    paid = rec.reconcile([intent(1)], [])
    left = rec.reconcile([intent(1, status="requires_payment_method")], [])

    assert "no such payment" in notes(paid)["ENEI-0000000001"]
    assert left.problems == [] and left.sales == []


def test_a_full_refund_in_the_dashboard_with_a_valid_ticket_is_a_problem():
    report = rec.reconcile([intent(1, refunded=4594)], [tx(1)])

    assert "still valid" in notes(report)["ENEI-0000000001"]


def test_a_partial_refund_is_listed_but_is_not_a_problem():
    report = rec.reconcile([intent(1, refunded=1000)], [tx(1)])

    assert report.problems == []
    assert "partial refund of 10.00 EUR" in report.infos[0].note


def test_a_refunded_ticket_matches_a_full_refund_and_a_partial_one_is_listed():
    good = rec.reconcile([intent(1, refunded=4594)], [tx(1, S.REFUNDED)])
    bad = rec.reconcile([intent(1)], [tx(1, S.REFUNDED)])

    assert good.problems == [] and good.infos == []
    assert bad.problems == []  # a ticket cancelled by hand after a partial refund
    assert "partial refund, or none" in bad.infos[0].note


def test_a_payment_waiting_to_be_paid_back_is_only_listed():
    report = rec.reconcile([intent(1)], [tx(1, S.REFUND_DUE)])

    assert report.problems == []
    assert "refund --due" in report.infos[0].note


def test_a_payment_whose_id_was_never_saved_pairs_by_the_reference():
    report = rec.reconcile([intent(1)], [tx(1, with_intent=False)])

    assert report.problems == []


def test_another_try_of_the_same_reference_is_not_a_missing_sale():
    """The site pairs the payment with one PaymentIntent; a cancelled one is noise."""
    other = intent(9, status="canceled", reference="ENEI-0000000001")

    report = rec.reconcile([intent(1), other], [tx(1)])

    assert report.problems == []


def test_unfinished_payments_on_the_site_are_ignored():
    report = rec.reconcile([], [tx(1, S.PENDING), tx(2, S.EXPIRED, with_intent=False)])

    assert report.problems == [] and report.sales == []


def test_the_totals_and_the_fees():
    report = rec.reconcile(
        [intent(1, fee=94), intent(2, refunded=4594, fee=94)],
        [tx(1), tx(2, S.REFUNDED)],
    )

    t = rec.totals(report)
    assert (t["stripe_paid"], t["stripe_cents"], t["stripe_refunded_cents"]) == (
        2,
        9188,
        4594,
    )
    assert (t["site_counted"], t["site_cents"]) == (2, 9188)
    assert (t["fee_cents"], t["net_cents"]) == (188, 9000)


def test_the_stripe_list_is_read_page_by_page_with_the_charge_expanded():
    calls = []
    pages = {
        None: {"data": [{"id": "pi_a"}, {"id": "pi_b"}], "has_more": True},
        "pi_b": {"data": [{"id": "pi_c"}], "has_more": False},
    }

    def read(path, params):
        calls.append((path, dict(params)))
        return pages[params.get("starting_after")]

    since = datetime(2026, 11, 9, tzinfo=UTC)
    found = rec.fetch_intents(read, since=since, fees=True)

    assert [i["id"] for i in found] == ["pi_a", "pi_b", "pi_c"]
    assert {path for path, _ in calls} == {"/payment_intents"}
    assert calls[0][1]["expand[]"] == "data.latest_charge.balance_transaction"
    assert calls[0][1]["created[gte]"] == int(since.timestamp())
    assert calls[1][1]["starting_after"] == "pi_b"


TIERS = {1: "geral"}


def _both():
    """A paid sale, a checkout nobody finished and a sale only the site knows."""
    abandoned = intent(2, status="requires_payment_method")
    return rec.reconcile(
        [intent(1), abandoned], [tx(1), tx(3, S.PENDING, with_intent=False)], TIERS
    )


def test_every_payment_of_either_side_is_a_row_and_the_unfinished_are_marked():
    report = _both()

    assert len(report.rows) == 3
    assert [r.reference for r in report.sales] == ["ENEI-0000000001"]


def test_the_site_listing_has_every_site_payment_and_no_stripe_only_ones():
    report = _both()

    rows = rec.rows_of(report, "site", paid_only=False)

    assert [r.reference for r in rows] == ["ENEI-0000000001", "ENEI-0000000003"]
    assert rec.rows_of(report, "site", paid_only=True)[0].reference == "ENEI-0000000001"


def test_the_stripe_listing_has_every_payment_intent_and_no_site_only_ones():
    report = _both()

    rows = rec.rows_of(report, "stripe", paid_only=False)

    assert [r.payment_intent for r in rows] == ["pi_001", "pi_002"]
    assert [
        r.payment_intent for r in rec.rows_of(report, "stripe", paid_only=True)
    ] == ["pi_001"]


def test_the_side_by_side_listing_has_one_row_for_each_payment_on_both_sides():
    report = _both()

    rows = rec.rows_of(report, "side", paid_only=False)
    columns = rec.columns_of("side", fees=False, with_nif=False)

    assert len(rows) == 3
    assert [heading for _, heading in columns][:6] == [
        "reference",
        "site_status",
        "site_amount_cents",
        "stripe_status",
        "stripe_amount_cents",
        "stripe_refunded_cents",
    ]


def test_the_tier_is_named_and_the_nif_only_shows_when_asked():
    transaction = tx(1)
    transaction.ticket_tier_id = 1
    transaction.nif = "504035266"
    report = rec.reconcile([intent(1)], [transaction], TIERS)

    assert report.rows[0].site_tier == "geral"
    plain = [h for _, h in rec.columns_of("all", fees=False, with_nif=False)]
    with_nif = [h for _, h in rec.columns_of("all", fees=False, with_nif=True)]
    assert "nif" not in plain and with_nif[-1] == "nif"
    assert "nif" not in [
        h for _, h in rec.columns_of("stripe", fees=False, with_nif=True)
    ]


def test_the_csv_follows_the_chosen_columns_and_has_no_personal_data(tmp_path):
    report = rec.reconcile([intent(1)], [tx(1)], TIERS)
    columns = rec.columns_of("all", fees=True, with_nif=False)
    path = tmp_path / "vendas.csv"

    rec.write_csv(columns, rec.rows_of(report, "all", paid_only=False), str(path))

    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[0] == [heading for _, heading in columns]
    assert {"nif", "phone", "email", "name"}.isdisjoint(rows[0])
    assert rows[1][rows[0].index("reference")] == "ENEI-0000000001"
    assert "stripe_fee_cents" in rows[0]


def test_the_printed_problems_name_each_one_and_no_personal_data(capsys):
    report = rec.reconcile([intent(1), intent(2)], [tx(1, S.PENDING), tx(2)])

    rec.print_summary(report, fees=False)
    rec.print_problems(report)

    out = capsys.readouterr().out
    assert "!! ENEI-0000000001" in out
    assert "1 problem(s)." in out
    assert "ENEI-0000000002" not in out


def test_the_table_lines_up_the_columns(capsys):
    report = _both()
    columns = rec.columns_of("site", fees=False, with_nif=False)

    rec.print_table(columns, rec.rows_of(report, "site", paid_only=False))

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split()[:2] == ["reference", "tier"]
    assert lines[1].startswith("ENEI-0000000001  geral")


class _NoDatabase:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def _run(monkeypatch, capsys, *argv, intents=None, transactions=None):
    monkeypatch.setattr(rec, "SessionLocal", _NoDatabase)
    monkeypatch.setattr(rec, "fetch_intents", lambda read, **kw: intents or [])
    monkeypatch.setattr(rec, "load_transactions", lambda db, since: transactions or [])
    monkeypatch.setattr(rec, "load_tiers", lambda db: TIERS)
    code = rec.main(list(argv))
    return code, capsys.readouterr().out


def test_the_command_lists_each_choice_and_exits_1_only_on_a_problem(
    monkeypatch, capsys, tmp_path
):
    good = dict(intents=[intent(1)], transactions=[tx(1)])
    bad = dict(intents=[intent(1)], transactions=[tx(1, S.PENDING)])

    code, out = _run(monkeypatch, capsys, **good)
    assert code == 0 and "Every sale is counted" in out
    code, out = _run(monkeypatch, capsys, "--list", "site", **good)
    assert code == 0 and "ENEI-0000000001" in out and "geral" in out
    code, out = _run(monkeypatch, capsys, "--list", "stripe", **good)
    assert code == 0 and "pi_001" in out
    csv_path = tmp_path / "side.csv"
    code, out = _run(
        monkeypatch, capsys, "--list", "side", "--csv", str(csv_path), **bad
    )
    assert code == 1 and "1 problem(s)" in out
    assert "no ticket and no invoice" in csv_path.read_text(encoding="utf-8")


def test_the_nif_is_in_the_listing_only_with_the_flag(monkeypatch, capsys):
    transaction = tx(1)
    transaction.nif = "504035266"
    data = dict(intents=[intent(1)], transactions=[transaction])

    _, plain = _run(monkeypatch, capsys, "--list", "site", **data)
    _, asked = _run(monkeypatch, capsys, "--list", "site", "--with-nif", **data)

    assert "504035266" not in plain
    assert "504035266" in asked


def test_a_payment_of_another_product_of_the_account_is_not_ours_to_compare():
    """The Stripe account is shared: a payment with no ENEI reference is no problem."""
    other = intent(7, reference="sweat-camiseta")

    report = rec.reconcile([intent(1), other], [tx(1)])

    assert report.problems == []
    assert [r.payment_intent for r in report.others] == ["pi_007"]
    t = rec.totals(report)
    assert (t["stripe_paid"], t["other_paid"], t["other_cents"]) == (1, 1, 4594)
    assert [
        r.payment_intent for r in rec.rows_of(report, "stripe", paid_only=False)
    ] == [
        "pi_001",
        "pi_007",
    ]
    assert [r.payment_intent for r in rec.rows_of(report, "side", paid_only=False)] == [
        "pi_001"
    ]


def test_an_enei_reference_the_site_does_not_know_is_still_a_problem():
    report = rec.reconcile([intent(7)], [])

    assert "no such payment" in notes(report)["ENEI-0000000007"]
    assert report.others == []


NOW = datetime.fromtimestamp(1_700_000_000 + 10_000, UTC)


def test_a_mismatch_on_a_payment_made_minutes_ago_is_information_not_a_problem():
    young = intent(1)
    young["created"] = int(NOW.timestamp()) - 120  # two minutes ago
    old = intent(2)  # almost three hours before NOW

    report = rec.reconcile([young, old], [tx(1, S.PENDING), tx(2, S.PENDING)], now=NOW)

    assert [r.reference for r in report.problems] == ["ENEI-0000000002"]
    assert "recent" in report.infos[0].note
    assert report.infos[0].reference == "ENEI-0000000001"


def test_a_site_payment_stripe_does_not_have_is_also_given_a_grace():
    fresh = tx(1)
    fresh.created_at = NOW - timedelta(minutes=2)

    report = rec.reconcile([], [fresh], now=NOW)

    assert report.problems == []
    assert "recent" in report.infos[0].note


def test_refunded_at_stripe_but_still_refund_due_on_the_site_is_a_problem():
    report = rec.reconcile([intent(1, refunded=4594)], [tx(1, S.REFUND_DUE)])

    assert "still says refund_due" in notes(report)["ENEI-0000000001"]


def test_against_a_real_database_the_rows_pair_up_and_the_tier_is_named(db_session):
    """``load_transactions`` and ``load_tiers`` read what the site really stores."""
    from app.domains.payments.models import TicketTier, TicketTierPrice
    from app.domains.users.models import User
    from tests.helpers import seed_ticket_tiers

    seed_ticket_tiers(db_session)
    geral = db_session.scalar(
        select(TicketTierPrice).where(TicketTierPrice.tier == TicketTier.GERAL)
    )
    user = User(name="Ana", email="ana@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    paid = Transaction(
        reference="ENEI-0000000001",
        user_id=user.id,
        ticket_tier_id=geral.id,
        amount_cents=4594,
        status=S.CONFIRMED,
        phone="912345678",
        nif="504035266",
        provider="stripe",
        provider_reference="pi_001",
        expires_at=datetime(2023, 11, 14, tzinfo=UTC),
        confirmed_at=datetime(2023, 11, 14, 9, 5, tzinfo=UTC),
        created_at=datetime(2023, 11, 14, 9, 1, tzinfo=UTC),
    )
    simulated = Transaction(
        reference="ENEI-0000000002",
        user_id=user.id,
        ticket_tier_id=geral.id,
        amount_cents=4594,
        status=S.CONFIRMED,
        phone="912345678",
        provider="simulated",
        provider_reference="P-1",
        expires_at=datetime(2023, 11, 14, tzinfo=UTC),
    )
    db_session.add_all([paid, simulated])
    db_session.commit()

    transactions = rec.load_transactions(db_session, None)
    report = rec.reconcile(
        [intent(1)], transactions, rec.load_tiers(db_session), now=NOW
    )

    assert [t.reference for t in transactions] == ["ENEI-0000000001"]
    assert report.problems == []
    assert report.rows[0].site_tier == "geral" and report.rows[0].nif == "504035266"
    since = datetime(2023, 11, 15, tzinfo=UTC)
    assert rec.load_transactions(db_session, since) == []


def test_a_disputed_payment_is_a_problem_even_when_both_sides_agree_and_it_is_recent():
    disputed = intent(1)
    disputed["latest_charge"]["disputed"] = True
    disputed["created"] = int(NOW.timestamp()) - 60  # very recent: still not softened

    report = rec.reconcile([disputed, intent(2)], [tx(1), tx(2)], now=NOW)

    assert [r.reference for r in report.problems] == ["ENEI-0000000001"]
    assert "DISPUTED" in report.problems[0].note
    assert "answer it in the dashboard" in report.problems[0].note


def test_a_dispute_on_another_product_of_the_account_is_not_ours():
    other = intent(7, reference="sweat-camiseta")
    other["latest_charge"]["disputed"] = True

    report = rec.reconcile([other], [])

    assert report.problems == []


def test_text_that_comes_from_stripe_cannot_carry_control_characters_or_formulas(
    tmp_path,
):
    """The account is shared: another product's metadata is not ours to trust."""
    hostile = intent(7, reference='=HYPERLINK("x")\x1b[31m')
    hostile["id"] = "pi_007\x07"

    report = rec.reconcile([hostile], [])
    path = tmp_path / "x.csv"
    columns = rec.columns_of("stripe", fees=False, with_nif=False)
    rec.write_csv(columns, rec.rows_of(report, "stripe", paid_only=False), str(path))

    text = path.read_text(encoding="utf-8")
    assert "\x1b" not in text and "\x07" not in text
    assert not any(
        cell.startswith(("=", "+", "@"))
        for line in text.splitlines()
        for cell in line.split(",")
    )
    assert report.rows[0].reference == "HYPERLINKx31m"


def test_without_fee_data_the_summary_says_so_instead_of_printing_zero(capsys):
    """A key that cannot read balance transactions must not look like free payments."""
    rec.print_summary(rec.reconcile([intent(1)], [tx(1)]), fees=True)
    assert "fees: Stripe gave none" in capsys.readouterr().out

    rec.print_summary(rec.reconcile([intent(1, fee=94)], [tx(1)]), fees=True)
    out = capsys.readouterr().out
    assert "fees 0.94 EUR, net 45.00 EUR" in out
