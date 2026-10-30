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

export interface AgendaDay {
  /** Identificador do separador (`ag-tab-<key>`) e valor de `?dia=`. */
  key: 'quinta' | 'sexta' | 'sabado' | 'domingo';
  /** Dia, `AAAA-MM-DD`. */
  date: string;
  /** Nome do dia por extenso, como aparece na linha «Sexta-feira, 2 abril · 10 sessões». */
  label: string;
  /** A etiqueta pequena do botão do dia («SEXTA»). */
  tab: string;
  /** O número grande do botão do dia («2 Abr»). */
  short: string;
}

/** `encontro` (momentos: chegada, refeições, convívio), `palestras` e `workshops`. «Palestras» no filtro inclui os workshops. */
export type AgendaCategory = 'encontro' | 'palestras' | 'workshops';

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
  /** Fim, `AAAA-MM-DDTHH:MM`, hora de Lisboa: no mesmo dia ou, numa noite, na madrugada do dia seguinte. Sem valor, o cartão mostra só a hora de início. */
  end?: string;
  /** O separador do dia a que o item pertence, quando não é o da data de `start` (a discoteca de sexta começa à 00:00 de sábado e aparece em sexta). */
  day?: AgendaDay['key'];
  title: string;
  /** Etiqueta do tipo de sessão («Palestra», «Refeição»…). */
  kind: string;
  category: AgendaCategory;
  /** Cor do cartão. Sem valor, a da categoria (momentos em areia, palestras em azul, workshops em lilás). */
  tone?: 'azul';
  /** Local da sessão (sala, auditório…). Sem valor, a página diz que o local está por confirmar. */
  location?: string;
  /** Quem fala. Sem valor, a página diz que o orador está por anunciar (ver `announce`). */
  speaker?: AgendaSpeaker;
  /** Texto «por anunciar» quando ainda não há `speaker` (por omissão: «Orador a anunciar»). */
  announce?: string;
  /** `false` esconde o item sem o apagar. */
  visible?: boolean;
}

export const AGENDA_DAYS: AgendaDay[] = [
  { key: 'quinta', date: '2027-04-01', label: 'Quinta-feira, 1 abril', tab: 'QUINTA', short: '1 Abr' },
  { key: 'sexta', date: '2027-04-02', label: 'Sexta-feira, 2 abril', tab: 'SEXTA', short: '2 Abr' },
  { key: 'sabado', date: '2027-04-03', label: 'Sábado, 3 abril', tab: 'SÁBADO', short: '3 Abr' },
  { key: 'domingo', date: '2027-04-04', label: 'Domingo, 4 abril', tab: 'DOMINGO', short: '4 Abr' },
];

/**
 * Por ordem de hora. O programa vem do calendário enviado pela organização a 28/10/2026 (horas de fim incluídas). Os locais e
 * os oradores ainda não estão confirmados: a página diz «a confirmar» / «a anunciar». As noites que passam da meia-noite têm o
 * `end` no dia seguinte, e a discoteca de sexta (00:00 de sábado) leva `day: 'sexta'` para aparecer no separador de sexta.
 */
export const AGENDA: AgendaItem[] = [
  { id: 'qui-1600-sessao-de-boas-vindas', start: '2027-04-01T16:00', end: '2027-04-01T18:00', title: 'Sessão de boas-vindas', kind: 'Boas-vindas', category: 'encontro', tone: 'azul' },
  { id: 'qui-1900-jantar', start: '2027-04-01T19:00', end: '2027-04-01T20:30', title: 'Jantar', kind: 'Refeição', category: 'encontro', tone: 'azul' },
  { id: 'qui-2200-arraial', start: '2027-04-01T22:00', end: '2027-04-02T04:00', title: 'Arraial', kind: 'Noite', category: 'encontro', tone: 'azul' },
  { id: 'sex-0900-palestra', start: '2027-04-02T09:00', end: '2027-04-02T10:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sex-1000-palestra', start: '2027-04-02T10:00', end: '2027-04-02T11:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sex-1100-palestra', start: '2027-04-02T11:00', end: '2027-04-02T12:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sex-1200-almoco', start: '2027-04-02T12:00', end: '2027-04-02T14:00', title: 'Almoço', kind: 'Refeição', category: 'encontro' },
  { id: 'sex-1430-atividades', start: '2027-04-02T14:30', end: '2027-04-02T17:00', title: 'Atividades', kind: 'Atividades', category: 'workshops' },
  { id: 'sex-1500-palestra', start: '2027-04-02T15:00', end: '2027-04-02T16:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sex-1600-palestra', start: '2027-04-02T16:00', end: '2027-04-02T17:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sex-1700-palestra', start: '2027-04-02T17:00', end: '2027-04-02T18:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sex-1900-jantar', start: '2027-04-02T19:00', end: '2027-04-02T20:30', title: 'Jantar', kind: 'Refeição', category: 'encontro' },
  { id: 'sex-2100-dr-why', start: '2027-04-02T21:00', end: '2027-04-02T23:00', title: 'Dr Why', kind: 'Noite', category: 'encontro' },
  { id: 'sex-0000-discoteca', start: '2027-04-03T00:00', end: '2027-04-03T04:00', day: 'sexta', title: 'Discoteca', kind: 'Noite', category: 'encontro' },
  { id: 'sab-0900-palestra', start: '2027-04-03T09:00', end: '2027-04-03T10:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sab-1000-palestra', start: '2027-04-03T10:00', end: '2027-04-03T11:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sab-1100-palestra', start: '2027-04-03T11:00', end: '2027-04-03T12:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sab-1200-almoco', start: '2027-04-03T12:00', end: '2027-04-03T14:00', title: 'Almoço', kind: 'Refeição', category: 'encontro' },
  { id: 'sab-1430-atividades', start: '2027-04-03T14:30', end: '2027-04-03T17:00', title: 'Atividades', kind: 'Atividades', category: 'workshops' },
  { id: 'sab-1500-palestra', start: '2027-04-03T15:00', end: '2027-04-03T16:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sab-1600-palestra', start: '2027-04-03T16:00', end: '2027-04-03T17:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sab-1700-palestra', start: '2027-04-03T17:00', end: '2027-04-03T18:00', title: 'Palestra', kind: 'Palestra', category: 'palestras' },
  { id: 'sab-1900-jantar', start: '2027-04-03T19:00', end: '2027-04-03T20:30', title: 'Jantar', kind: 'Refeição', category: 'encontro' },
  { id: 'sab-2130-peddy-paper', start: '2027-04-03T21:30', end: '2027-04-03T22:30', title: 'Peddy Paper', kind: 'Noite', category: 'encontro' },
  { id: 'sab-2130-rally-tascas', start: '2027-04-03T21:30', end: '2027-04-03T22:30', title: 'Rally Tascas', kind: 'Noite', category: 'encontro' },
  { id: 'dom-0900-atividades', start: '2027-04-04T09:00', end: '2027-04-04T11:00', title: 'Atividades', kind: 'Atividades', category: 'encontro' },
  { id: 'dom-1130-almoco', start: '2027-04-04T11:30', end: '2027-04-04T13:00', title: 'Almoço', kind: 'Refeição', category: 'encontro' },
  { id: 'dom-1300-tomas-banho', start: '2027-04-04T13:00', end: '2027-04-04T14:00', title: 'Tomás banho', kind: 'Social', category: 'encontro' },
  { id: 'dom-1500-tertulia-de-encerramento', start: '2027-04-04T15:00', end: '2027-04-04T17:00', title: 'Tertúlia de encerramento', kind: 'Tertúlia', category: 'palestras' },
  { id: 'dom-1700-entrega-de-premios', start: '2027-04-04T17:00', end: '2027-04-04T18:00', title: 'Entrega de prémios', kind: 'Encerramento', category: 'encontro' },
];

/** `HH:MM` de um item. */
export const timeOf = (item: AgendaItem) => item.start.slice(11, 16);
/** `HH:MM` do fim de um item, se tiver. */
export const endOf = (item: AgendaItem) => (item.end ? item.end.slice(11, 16) : null);
/** «11:00 – 12:00», ou só «11:00» sem hora de fim. */
export const timeRange = (item: AgendaItem) => (item.end ? `${timeOf(item)} – ${endOf(item)}` : timeOf(item));
/** Os itens visíveis de um dia, por ordem de hora. */
export const itemsOfDay = (items: AgendaItem[], day: AgendaDay) =>
  items.filter((item) => item.visible !== false && (item.day ? item.day === day.key : item.start.startsWith(day.date))).sort((a, b) => a.start.localeCompare(b.start));

/** Cartão com retrato (palestras e workshops) ou cartão de momento (o resto). */
export const cardOf = (item: AgendaItem): 'speaker' | 'moment' => (item.category === 'encontro' ? 'moment' : 'speaker');

/** O que se mostra enquanto o local não está confirmado. */
export const pendingLocation = (item: AgendaItem) =>
  item.category === 'workshops' ? 'Salas a confirmar' : item.category === 'palestras' && item.kind === 'Palestra' ? 'Auditório a confirmar' : 'Local a confirmar';

/** O que se mostra enquanto o orador não está confirmado. */
export const pendingSpeaker = (item: AgendaItem) =>
  item.announce ?? (item.category === 'workshops' ? 'Oradores e facilitadores a anunciar' : item.kind === 'Tertúlia' ? 'Convidados a anunciar' : 'Orador a anunciar');

/** O filtro «Palestras» inclui os workshops; os outros filtros são a categoria exata. */
export const matchesFilter = (item: AgendaItem, filter: 'all' | 'palestras' | 'workshops' | 'saved', saved: ReadonlySet<string>) =>
  filter === 'all'
    ? true
    : filter === 'saved'
      ? saved.has(item.id)
      : item.category === filter || (filter === 'palestras' && item.category === 'workshops');
