/** Dinheiro: o backend fala em cêntimos. `null` é uma modalidade ainda sem preço. */
export function formatPrice(cents: number | null, currency = "EUR"): string {
  if (cents === null) return "A confirmar";
  return new Intl.NumberFormat("pt-PT", { style: "currency", currency }).format(cents / 100);
}

/** O telemóvel como se escreve em Portugal: 9 dígitos, sem indicativo nem espaços. */
export function normalizePhone(raw: string): string {
  let digits = raw.replace(/\D/g, "");
  if (digits.startsWith("00351")) digits = digits.slice(5);
  else if (digits.startsWith("351") && digits.length === 12) digits = digits.slice(3);
  return digits;
}

export const isPortuguesePhone = (raw: string) => /^9\d{8}$/.test(normalizePhone(raw));

/** «2 de novembro às 09:00», na hora de Lisboa, de uma data ISO 8601. */
export function formatOpeningTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("pt-PT", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Lisbon",
  }).format(date);
}
