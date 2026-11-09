import pytest

from app.domains.students.institutions import (
    institution_by_key,
    institutions,
    is_short_acronym,
    is_valid_nipc,
    match_institution,
    normalize,
)
from app.domains.users.enums import PortugueseInstitution


def test_every_institution_of_the_list_is_there():
    keys = {item.key for item in institutions()}

    assert keys == set(PortugueseInstitution.__members__)
    assert len(keys) > 100


def test_normalize_ignores_case_accents_and_punctuation():
    assert normalize("  Universidade  de ÉVORA, (Portugal)! ") == (
        "universidade de evora portugal"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Universidade do Algarve",
        "UNIVERSIDADE DO ALGARVE",
        "universidade algarve",
        "Univ. do Algarve",
        "Universidade do Algarve - Campus de Gambelas",
        "UALG",
        "UAlg",
    ],
)
def test_names_acronyms_and_variants_find_the_institution(text):
    assert match_institution(text).key == "UALG"


def test_variants_are_made_by_code_from_the_name():
    ipb = institution_by_key("IPB")

    assert "instituto politecnico de braganca" in ipb.variants
    assert match_institution("Instituto Politécnico de Bragança").key == "IPB"


@pytest.mark.parametrize("text", ["UP", "UL", "UC", "UA", "ISG", "UM", "NOVA"])
def test_short_acronyms_match_only_by_equality(text):
    assert is_short_acronym(text)
    assert match_institution(text) is not None
    assert match_institution(f"Faculdade da {text}") is None
    assert match_institution(f"{text} Lisboa") is None


def test_a_short_acronym_inside_a_long_text_does_not_match():
    assert match_institution("Associação de Estudantes UP e outros") is None


def test_a_long_acronym_matches_as_a_word_of_a_longer_text():
    assert match_institution("Selo da ULUSOFONA em Lisboa").key == "ULUSOFONA"
    assert not is_short_acronym("ULUSOFONA")


def test_ambiguous_names_find_nothing():
    # The same school name exists in several universities.
    assert match_institution("Escola Superior de Saúde") is None


def test_unknown_text_finds_nothing():
    assert match_institution("Banco de Portugal") is None
    assert match_institution("") is None


@pytest.mark.parametrize("nipc", ["501413197", "502011378", "500745471"])
def test_valid_nipc(nipc):
    assert is_valid_nipc(nipc)


@pytest.mark.parametrize(
    "nipc", ["501413198", "12345678", "5014131970", "abcdefghi", ""]
)
def test_invalid_nipc(nipc):
    assert not is_valid_nipc(nipc)
