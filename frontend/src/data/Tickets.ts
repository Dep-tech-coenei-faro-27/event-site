// Modalidades de bilhete. O `slug` é o mesmo valor que a API usa (TicketTier no backend)
// e vai no URL do checkout: /bilhetes/checkout?bilhete=<slug>
// Os nomes e preços que contam são os de GET /api/payment/tiers; isto é só o texto da
// página dos Bilhetes e a descrição curta de cada modalidade no checkout.
export type TicketSlug = 'acesso' | 'refeicoes' | 'completo' | 'geral';

export const TICKET_NAMES: Record<TicketSlug, string> = {
    acesso: 'Apenas acesso',
    refeicoes: 'Acesso + refeições',
    completo: 'Experiência completa',
    geral: 'Passe geral',
};

// Uma modalidade nova da API sem entrada aqui aparece só com o nome.
export const TICKET_DESCRIPTIONS: Record<string, string> = {
    acesso: 'Entrada no evento e programa geral.',
    refeicoes: 'Entrada no evento e refeições incluídas.',
    completo: 'Evento, refeições e alojamento coletivo.',
    geral: 'Acesso ao programa completo.',
};

// Modalidade em destaque no design («Recomendado»).
export const FEATURED_TICKET = 'completo';

export const checkoutPath = (slug: TicketSlug) => `/bilhetes/checkout?bilhete=${slug}`;
