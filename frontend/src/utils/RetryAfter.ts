/**
 * Mensagem para respostas 429, a partir do header Retry-After
 * (segundos ou data HTTP). Sem header válido, usa uma mensagem genérica.
 */
export function retryAfterMessage(
  res: Response,
  base = "Demasiadas tentativas.",
): string {
  const raw = res.headers.get("Retry-After");
  if (!raw) return `${base} Tenta novamente mais tarde.`;

  let secs = Number(raw);
  if (!Number.isFinite(secs)) {
    const date = Date.parse(raw);
    secs = Number.isNaN(date) ? 0 : (date - Date.now()) / 1000;
  }
  if (secs <= 0) return `${base} Tenta novamente mais tarde.`;

  if (secs < 60) {
    const s = Math.ceil(secs);
    return `${base} Tenta novamente dentro de ${s} ${s === 1 ? "segundo" : "segundos"}.`;
  }
  const m = Math.ceil(secs / 60);
  return `${base} Tenta novamente dentro de ${m} ${m === 1 ? "minuto" : "minutos"}.`;
}