// O backend manda as datas em ISO. Em Postgres (staging e produção) vêm com fuso
// (`2026-10-17T01:35:28+01:00`), mas em SQLite (desenvolvimento local e testes) vêm SEM fuso
// (`2026-10-17T00:35:28`) e são UTC. O `Date.parse` lê uma data sem fuso como hora local, o que
// em Portugal no verão desloca o prazo uma hora. Aqui uma data sem fuso é sempre UTC.

const HAS_ZONE = /(Z|[+-]\d{2}(:?\d{2})?)$/i;

/** Milissegundos desde 1970 de uma data da API; `NaN` se não for uma data. */
export function parseServerDate(value: string): number {
  const text = value.trim();
  const hasTime = text.includes("T");
  return Date.parse(hasTime && !HAS_ZONE.test(text) ? `${text}Z` : text);
}
