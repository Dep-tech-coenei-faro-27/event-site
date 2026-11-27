import pytest

from app.domains.payments.discounts import (
    DISCOUNT_CODES,
    discount_percent,
    normalize_discount_code,
    price_with_discount,
)


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        (4594, 4135),  # 459.4 off -> 459
        (1142, 1028),  # 114.2 off -> 114
        (1005, 904),  # 100.5 off rounds half up -> 101
        (7132, 6419),  # 713.2 off -> 713
        (100, 90),
    ],
)
def test_ten_percent_off_rounds_the_discount_to_the_cent(price, expected):
    assert price_with_discount(price, 10) == expected


def test_the_code_is_compared_without_case_or_spaces():
    assert normalize_discount_code(" algarve evolution ") == "ALGARVEEVOLUTION"
    assert normalize_discount_code("   ") is None
    assert normalize_discount_code(None) is None


@pytest.mark.parametrize(
    "lookalike",
    [
        "ALGARVEEVOLUTıON",  # dotless i
        "ALGARVEEVOLUTİON",  # dotted capital I
        "ſlgarveevolution",  # long s
        "ＡＬＧＡＲＶＥＥＶＯＬＵＴＩＯＮ",  # full-width letters
        "ALGARVE\u200bEVOLUTION",  # zero-width space
    ],
)
def test_a_lookalike_spelling_is_not_the_code(lookalike):
    assert discount_percent(normalize_discount_code(lookalike) or "") is None


def test_the_only_code_is_ten_percent():
    assert DISCOUNT_CODES == {"ALGARVEEVOLUTION": 10}
    assert discount_percent("ALGARVEEVOLUTION") == 10
    assert discount_percent("OTHER") is None
