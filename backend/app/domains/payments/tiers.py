from dataclasses import dataclass

from app.domains.payments.models import TicketTier


@dataclass(frozen=True)
class TicketTierSpec:
    tier: TicketTier
    name: str
    is_student: bool


TIER_SPECS: dict[TicketTier, TicketTierSpec] = {
    TicketTier.ACESSO: TicketTierSpec(TicketTier.ACESSO, "Apenas acesso", True),
    TicketTier.REFEICOES: TicketTierSpec(
        TicketTier.REFEICOES, "Acesso + refeições", True
    ),
    TicketTier.COMPLETO: TicketTierSpec(
        TicketTier.COMPLETO, "Experiência completa", True
    ),
    TicketTier.GERAL: TicketTierSpec(TicketTier.GERAL, "Passe geral", False),
    TicketTier.GERAL_REFEICOES: TicketTierSpec(
        TicketTier.GERAL_REFEICOES, "Passe geral + refeições", False
    ),
}
