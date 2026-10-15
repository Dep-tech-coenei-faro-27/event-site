import unicodedata
from typing import Annotated

from pydantic import AfterValidator, EmailStr
from pydantic_core import PydanticCustomError

INVISIBLE_OR_CONTROL = {"Cc", "Cf", "Cs", "Co", "Cn"}


def validate_name(value: str) -> str:
    """Trim a name and refuse blank, invisible or markup-like values."""
    name = value.strip()
    rules: list[str] = []

    if not name:
        rules.append("blank")
    else:
        if any(unicodedata.category(char) in INVISIBLE_OR_CONTROL for char in name):
            rules.append("invalid_characters")
        if "<" in name or ">" in name:
            rules.append("invalid_characters")
        if not any(unicodedata.category(char).startswith("L") for char in name):
            rules.append("no_letter")

    if rules:
        raise PydanticCustomError(
            "name_invalid", "Name is not valid", {"rules": sorted(set(rules))}
        )
    return name


def require_ascii_email(value: str) -> str:
    if not value.isascii():
        raise PydanticCustomError(
            "email_not_ascii", "Email must use ASCII characters only"
        )
    return value


AsciiEmail = Annotated[EmailStr, AfterValidator(require_ascii_email)]
