// Modalidades de bilhete. O `slug` é o mesmo valor que a API usa (TicketTier no backend)
// e vai no URL do checkout: /bilhetes/checkout?bilhete=<slug>
export type TicketSlug = 'acesso' | 'refeicoes' | 'completo' | 'geral';

export const TICKET_NAMES: Record<TicketSlug, string> = {
    acesso: 'Apenas acesso',
    refeicoes: 'Acesso + refeições',
    completo: 'Experiência completa',
    geral: 'Passe geral',
};

export const isTicketSlug = (value: string | null): value is TicketSlug =>
    value !== null && Object.hasOwn(TICKET_NAMES, value);

export const checkoutPath = (slug: TicketSlug) => `/bilhetes/checkout?bilhete=${slug}`;
