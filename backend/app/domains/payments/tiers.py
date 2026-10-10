from dataclasses import dataclass

from app.core.config import settings
from app.domains.payments.models import TicketTier


@dataclass(frozen=True)
class TicketTierSpec:
    tier: TicketTier
    name: str
    is_student: bool
    price_setting: str


TIER_SPECS: dict[TicketTier, TicketTierSpec] = {
    TicketTier.ACESSO: TicketTierSpec(
        TicketTier.ACESSO, "Apenas acesso", True, "TICKET_PRICE_ACESSO_CENTS"
    ),
    TicketTier.REFEICOES: TicketTierSpec(
        TicketTier.REFEICOES,
        "Acesso + refeições",
        True,
        "TICKET_PRICE_REFEICOES_CENTS",
    ),
    TicketTier.COMPLETO: TicketTierSpec(
        TicketTier.COMPLETO,
        "Experiência completa",
        True,
        "TICKET_PRICE_COMPLETO_CENTS",
    ),
    TicketTier.GERAL: TicketTierSpec(
        TicketTier.GERAL, "Passe geral", False, "TICKET_PRICE_GERAL_CENTS"
    ),
}


def tier_price_cents(tier: TicketTier) -> int:
    """The configured price (with VAT), in cents. Never taken from the client."""
    return int(getattr(settings, TIER_SPECS[tier].price_setting))
