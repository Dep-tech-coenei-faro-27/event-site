const formatters = new Map<string, Intl.NumberFormat>();

/** `4500` → `45,00 €`. Os valores da API vêm sempre em cêntimos. */
export function formatCents(cents: number, currency = 'EUR'): string {
  let fmt = formatters.get(currency);
  if (!fmt) {
    fmt = new Intl.NumberFormat('pt-PT', { style: 'currency', currency });
    formatters.set(currency, fmt);
  }
  return fmt.format(cents / 100);
}
