/**
 * Segundos de espera indicados pelo header Retry-After (segundos ou data HTTP).
 * Devolve 0 quando falta ou não se percebe.
 */
export function retryAfterSeconds(raw: string | null): number {
  if (!raw) return 0;
  const secs = Number(raw);
  if (Number.isFinite(secs)) return Math.max(0, secs);
  const date = Date.parse(raw);
  return Number.isNaN(date) ? 0 : Math.max(0, (date - Date.now()) / 1000);
}

/**
 * Mensagem para respostas 429, a partir do header Retry-After
 * (segundos ou data HTTP). Sem header válido, usa uma mensagem genérica.
 */
export function retryAfterMessage(
  raw: string | null,
  base = "Demasiadas tentativas.",
): string {
  const secs = retryAfterSeconds(raw);
  if (secs <= 0) return `${base} Tenta novamente mais tarde.`;

  if (secs < 60) {
    const s = Math.ceil(secs);
    return `${base} Tenta novamente dentro de ${s} ${s === 1 ? "segundo" : "segundos"}.`;
  }
  const m = Math.ceil(secs / 60);
  return `${base} Tenta novamente dentro de ${m} ${m === 1 ? "minuto" : "minutos"}.`;
}