// Versão e data de cada documento legal. É a única fonte: as páginas legais, o aviso do registo e a
// versão que o servidor guarda quando alguém aceita os termos (`CURRENT_TERMS_VERSION`, no backend)
// vêm daqui. Ao mudar um documento, mude só a versão e a data dele neste ficheiro (e a versão dos
// termos no backend; o teste `LegalDocs.test.ts` avisa se ficarem diferentes).
export interface LegalDoc {
  version: string;
  /** Data da última alteração, em ISO (AAAA-MM-DD). */
  updated: string;
}

export const LEGAL_DOCS = {
  termos: { version: '1.1', updated: '2026-11-06' },
  privacidade: { version: '1.0', updated: '2026-10-08' },
  acessibilidade: { version: '1.2', updated: '2026-11-08' },
} as const satisfies Record<string, LegalDoc>;

const MONTHS = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
];

/** "2026-11-06" passa a "6 de novembro de 2026". */
export function formatLegalDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} de ${MONTHS[month - 1]} de ${year}`;
}

/** As propriedades que a `LegalPageLayout` pede, a partir do documento. */
export function legalMeta(doc: LegalDoc) {
  return { version: doc.version, lastUpdated: formatLegalDate(doc.updated), lastUpdatedISO: doc.updated };
}
