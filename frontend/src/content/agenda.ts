/**
 * Fonte única da Agenda. Para mudar o programa edita-se só este ficheiro (ver `README.md` desta pasta): a página, os
 * separadores dos dias e os testes de esquema (`agenda.test.ts`) leem daqui.
 *
 * As horas são horas de Lisboa (`Europe/Lisbon`), sem fuso no texto; durante o evento (1 a 4 de abril de 2027) Lisboa
 * está em hora de verão (UTC+1).
 */

export const AGENDA_TIMEZONE = 'Europe/Lisbon';
/** Desfasamento de Lisboa em todos os dias do evento (hora de verão). Os testes confirmam-no com `Intl`. */
export const AGENDA_UTC_OFFSET = '+01:00';

export type AgendaTone = 'sand' | 'cyan' | 'teal' | 'coral' | 'periwinkle';

export interface AgendaDay {
  /** Identificador do separador (`#tab-<key>`, `#agenda-<key>`). */
  key: 'quinta' | 'sexta' | 'sabado' | 'domingo';
  /** Dia, `AAAA-MM-DD`. */
  date: string;
  weekday: string;
  short: string;
  label: string;
}

export interface AgendaSpeaker {
  name: string;
  company?: string;
  /** Nome do ficheiro em `src/assets/speakers/` (por exemplo `ana-silva.webp`). Exige `photoAlt`. */
  photo?: string;
  photoAlt?: string;
}

export interface AgendaItem {
  /** Estável: não muda se o item mudar de hora ou de dia (as inscrições vão ligar-se a este identificador). */
  id: string;
  /** `AAAA-MM-DDTHH:MM`, hora de Lisboa. */
  start: string;
  title: string;
  tag: { label: string; tone: AgendaTone };
  /** Local da sessão (sala, auditório…). */
  location?: string;
  speaker?: AgendaSpeaker;
  /** `false` esconde o item sem o apagar. */
  visible?: boolean;
}

export const AGENDA_DAYS: AgendaDay[] = [
  { key: 'quinta', date: '2027-04-01', weekday: 'Quinta', short: '1 Abr', label: 'Quinta-feira · 1 abril' },
  { key: 'sexta', date: '2027-04-02', weekday: 'Sexta', short: '2 Abr', label: 'Sexta-feira · 2 abril' },
  { key: 'sabado', date: '2027-04-03', weekday: 'Sábado', short: '3 Abr', label: 'Sábado · 3 abril' },
  { key: 'domingo', date: '2027-04-04', weekday: 'Domingo', short: '4 Abr', label: 'Domingo · 4 abril' },
];

/** Por ordem de hora. */
export const AGENDA: AgendaItem[] = [
  { id: 'qui-1400-check-ins', start: '2027-04-01T14:00', title: 'Check-ins', tag: { label: 'Check-in', tone: 'sand' } },
  { id: 'qui-1800-sessao-de-boas-vindas', start: '2027-04-01T18:00', title: 'Sessão de boas-vindas', tag: { label: 'Boas-vindas', tone: 'cyan' } },
  { id: 'qui-2000-jantar-e-arraial-academico', start: '2027-04-01T20:00', title: 'Jantar e arraial académico', tag: { label: 'Jantar', tone: 'teal' } },
  { id: 'sex-1000-palestra-e-workshops-1-2-e-3', start: '2027-04-02T10:00', title: 'Palestra e workshops #1, #2 e #3', tag: { label: 'Palestra / workshop', tone: 'coral' } },
  { id: 'sex-1100-palestra', start: '2027-04-02T11:00', title: 'Palestra', tag: { label: 'Palestra', tone: 'cyan' } },
  { id: 'sex-1200-almoco', start: '2027-04-02T12:00', title: 'Almoço', tag: { label: 'Refeição', tone: 'teal' } },
  { id: 'sex-1400-palestra-e-workshops-4-5-e-6', start: '2027-04-02T14:00', title: 'Palestra e workshops #4, #5 e #6', tag: { label: 'Palestra / workshop', tone: 'coral' } },
  { id: 'sex-1500-palestra', start: '2027-04-02T15:00', title: 'Palestra', tag: { label: 'Palestra', tone: 'cyan' } },
  { id: 'sex-1630-coffee-break', start: '2027-04-02T16:30', title: 'Coffee break', tag: { label: 'Networking', tone: 'sand' } },
  { id: 'sex-1700-palestra', start: '2027-04-02T17:00', title: 'Palestra', tag: { label: 'Palestra', tone: 'cyan' } },
  { id: 'sex-1800-tertulia', start: '2027-04-02T18:00', title: 'Tertúlia', tag: { label: 'Tertúlia', tone: 'periwinkle' } },
  { id: 'sex-2000-jantar', start: '2027-04-02T20:00', title: 'Jantar', tag: { label: 'Refeição', tone: 'teal' } },
  { id: 'sex-2200-atividades-noturnas', start: '2027-04-02T22:00', title: 'Atividades noturnas', tag: { label: 'Noite', tone: 'periwinkle' } },
  { id: 'sab-1000-palestra-e-workshops-10-11-e-12', start: '2027-04-03T10:00', title: 'Palestra e workshops #10, #11 e #12', tag: { label: 'Palestra / workshop', tone: 'coral' } },
  { id: 'sab-1100-palestra', start: '2027-04-03T11:00', title: 'Palestra', tag: { label: 'Palestra', tone: 'cyan' } },
  { id: 'sab-1200-almoco', start: '2027-04-03T12:00', title: 'Almoço', tag: { label: 'Refeição', tone: 'teal' } },
  { id: 'sab-1400-palestra-e-workshops-13-14-e-15', start: '2027-04-03T14:00', title: 'Palestra e workshops #13, #14 e #15', tag: { label: 'Palestra / workshop', tone: 'coral' } },
  { id: 'sab-1500-palestra', start: '2027-04-03T15:00', title: 'Palestra', tag: { label: 'Palestra', tone: 'cyan' } },
  { id: 'sab-1630-coffee-break', start: '2027-04-03T16:30', title: 'Coffee break', tag: { label: 'Networking', tone: 'sand' } },
  { id: 'sab-1700-palestra', start: '2027-04-03T17:00', title: 'Palestra', tag: { label: 'Palestra', tone: 'cyan' } },
  { id: 'sab-1800-tertulia', start: '2027-04-03T18:00', title: 'Tertúlia', tag: { label: 'Tertúlia', tone: 'periwinkle' } },
  { id: 'sab-2000-jantar', start: '2027-04-03T20:00', title: 'Jantar', tag: { label: 'Refeição', tone: 'teal' } },
  { id: 'sab-2200-atividades-noturnas', start: '2027-04-03T22:00', title: 'Atividades noturnas', tag: { label: 'Noite', tone: 'periwinkle' } },
  { id: 'dom-1000-nascer-do-sol-na-praia', start: '2027-04-04T10:00', title: 'Nascer do sol na praia', tag: { label: 'Social', tone: 'sand' } },
  { id: 'dom-1200-almoco', start: '2027-04-04T12:00', title: 'Almoço', tag: { label: 'Refeição', tone: 'teal' } },
  { id: 'dom-1400-tertulia', start: '2027-04-04T14:00', title: 'Tertúlia', tag: { label: 'Tertúlia', tone: 'periwinkle' } },
  { id: 'dom-1600-sessao-de-encerramento', start: '2027-04-04T16:00', title: 'Sessão de encerramento', tag: { label: 'Encerramento', tone: 'cyan' } },
];

/** `HH:MM` de um item. */
export const timeOf = (item: AgendaItem) => item.start.slice(11, 16);
/** Os itens visíveis de um dia, por ordem de hora. */
export const itemsOfDay = (items: AgendaItem[], day: AgendaDay) =>
  items.filter((item) => item.visible !== false && item.start.startsWith(day.date)).sort((a, b) => a.start.localeCompare(b.start));
