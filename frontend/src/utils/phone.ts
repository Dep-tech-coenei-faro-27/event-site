// Telemóvel português para o MB Way: 9 dígitos, a começar por 91, 92, 93 ou 96.
// Aceita o que a pessoa escrever (espaços, hífens, +351 ou 00351), como o backend.
const PT_MOBILE = /^9[1236]\d{7}$/;

/** Devolve o número como `9XXXXXXXX`, ou `null` se não for um telemóvel português. */
export function normalizePtMobile(value: string): string | null {
  let digits = value.replace(/\D/g, '');
  if (digits.startsWith('00351')) digits = digits.slice(5);
  else if (digits.startsWith('351') && digits.length > 9) digits = digits.slice(3);
  return PT_MOBILE.test(digits) ? digits : null;
}

/** Mensagem de erro do campo, ou `null` se o número for válido. */
export function ptMobileError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return 'Indica o número de telemóvel.';
  if (/[^\d\s+().-]/.test(trimmed)) return 'O número só pode ter algarismos.';
  if (normalizePtMobile(trimmed)) return null;

  const digits = trimmed.replace(/\D/g, '').replace(/^(00351|351)(?=\d{9})/, '');
  if (digits.length !== 9) return 'O número tem de ter 9 algarismos.';
  return 'Indica um telemóvel português (começa por 91, 92, 93 ou 96).';
}
