/**
 * Número de contacto da conta: 9 a 15 dígitos, com ou sem + e indicativo. Aceita espaços, pontos, hífenes e
 * parênteses; o que se envia ao servidor é só o + opcional e os dígitos (o servidor volta a validar).
 * Não é o número do MB WAY do checkout, que tem de ser um telemóvel português.
 */
export function normalizeContactPhone(value: string): string {
  const cleaned = value.replace(/[\s.\-()]/g, "");
  return cleaned.startsWith("00") ? `+${cleaned.slice(2)}` : cleaned;
}

export function isContactPhone(value: string): boolean {
  return /^\+?[0-9]{9,15}$/.test(normalizeContactPhone(value));
}

export const CONTACT_PHONE_MESSAGE =
  "Indica um número com 9 a 15 dígitos, com ou sem indicativo (por exemplo 912 345 678 ou +351 912 345 678).";
