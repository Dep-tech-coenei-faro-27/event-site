"""The higher education institutions and how a name on a document finds one.

The list comes from ``PortugueseInstitution``. Besides the full name, each institution
has acronyms (written here) and variants (made by code from the name). A name found
on a document matches by its words, with accents, case and punctuation ignored.
Acronyms of 5 letters or fewer are short and ambiguous ("UP", "ISG"), so they only
match when they are the whole text, never as a word inside a longer one.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import cache

from app.domains.users.enums import PortugueseInstitution

SHORT_ACRONYM_LETTERS = 5

# Acronyms and short names people use for institutions. The enum member name
# (ULISBOA, ISCTE, ...) is always an acronym too.
EXTRA_ACRONYMS: dict[str, tuple[str, ...]] = {
    "ULISBOA": ("UL", "ULisboa"),
    "UPORTO": ("UP", "U.Porto"),
    "UCOIMBRA": ("UC",),
    "UNL": ("NOVA", "UNova", "NOVA ULisboa"),
    "UMINHO": ("UM",),
    "UA": ("UAveiro",),
    "UCA": ("UCP", "Católica"),
    "UALG": ("UAlg",),
    "UEVORA": ("UÉ", "UEvora"),
    "UTAD": ("UTAD",),
    "UAL": ("Autónoma",),
    "IPBEJA": ("IPBeja",),
    "IPB": ("IPBragança", "IPBraganca"),
    "IPCB": ("IPCastelo Branco",),
    "IPCA": ("IPCA",),
    "IPC": ("IPCoimbra",),
    "IPG": ("IPGuarda",),
    "IPL": ("IPLisboa",),
    "IPSANTAREM": ("IPSantarém", "IPSantarem"),
    "IPSETUBAL": ("IPSetúbal", "IPSetubal"),
    "IPT": ("IPTomar",),
    "IPVC": ("IPViana do Castelo",),
    "IPV": ("IPViseu",),
    "IPPORTALEGRE": ("IPPortalegre",),
}

# What the institutions call themselves; the enum has older or different forms.
PREFIX_SWAPS = (
    ("universidade politecnica", "instituto politecnico"),
    ("universidade", "univ"),
    ("instituto", "inst"),
    ("escola superior", "esc sup"),
)
SKIPPED_WORDS = {"de", "do", "da", "dos", "das", "e", "a", "o"}


def normalize(text: str) -> str:
    """Lowercase, no accents, punctuation as spaces, single spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain.lower()).split())


def letters_of(text: str) -> str:
    return normalize(text).replace(" ", "")


def is_short_acronym(text: str) -> bool:
    return len(letters_of(text)) <= SHORT_ACRONYM_LETTERS


@dataclass(frozen=True)
class Institution:
    key: str
    name: str
    acronyms: tuple[str, ...]
    variants: tuple[str, ...]


def _name_variants(name: str) -> set[str]:
    base = normalize(name)
    variants = {base}
    for old, new in PREFIX_SWAPS:
        if base.startswith(old):
            variants.add(new + base[len(old) :])
    variants |= {
        " ".join(word for word in variant.split() if word not in SKIPPED_WORDS)
        for variant in set(variants)
    }
    return variants


@cache
def institutions() -> tuple[Institution, ...]:
    result = []
    for key, member in PortugueseInstitution.__members__.items():
        # Members with the same name (a school of the same name in several
        # universities) are all kept, so a name that fits several is ambiguous.
        acronyms = {key, *EXTRA_ACRONYMS.get(key, ())}
        result.append(
            Institution(
                key=key,
                name=member.value,
                acronyms=tuple(sorted(acronyms)),
                variants=tuple(sorted(_name_variants(member.value))),
            )
        )
    return tuple(result)


def institution_by_key(key: str) -> Institution | None:
    return next((item for item in institutions() if item.key == key), None)


def _contains_words(haystack: str, needle: str) -> bool:
    return f" {needle} " in f" {haystack} "


def match_institution(text: str) -> Institution | None:
    """The institution a name refers to, or ``None`` if none or more than one fit.

    The longest match wins; two institutions matching equally well (for example
    schools that have the same name in different universities) are ambiguous.
    """
    candidate = normalize(text)
    if not candidate:
        return None

    scores: dict[str, int] = {}
    for item in institutions():
        best = 0
        for variant in item.variants:
            if variant == candidate or (
                len(letters_of(variant)) > SHORT_ACRONYM_LETTERS
                and _contains_words(candidate, variant)
            ):
                best = max(best, len(variant))
        for acronym in item.acronyms:
            acronym_text = normalize(acronym)
            if is_short_acronym(acronym):
                matches = acronym_text == candidate
            else:
                matches = _contains_words(candidate, acronym_text)
            if matches:
                best = max(best, len(acronym_text))
        if best:
            scores[item.key] = best

    if not scores:
        return None
    top = max(scores.values())
    winners = [key for key, score in scores.items() if score == top]
    if len(winners) != 1:
        return None
    return institution_by_key(winners[0])


def is_valid_nipc(value: str) -> bool:
    """Nine digits with the mod-11 check digit of the Portuguese tax number."""
    if not re.fullmatch(r"\d{9}", value):
        return False
    total = sum(int(digit) * weight for digit, weight in zip(value, range(9, 1, -1)))
    check = 11 - total % 11
    return int(value[8]) == (0 if check >= 10 else check)
