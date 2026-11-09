// NIF português: 9 algarismos, o último é o algarismo de controlo (módulo 11).

/** Só os algarismos (aceita espaços e o prefixo PT). */
export const cleanNif = (value: string) => value.replace(/^\s*PT/i, '').replace(/[\s.-]/g, '');

export function isValidNif(value: string): boolean {
  const nif = cleanNif(value);
  if (!/^\d{9}$/.test(nif)) return false;
  const sum = [...nif.slice(0, 8)].reduce((acc, d, i) => acc + Number(d) * (9 - i), 0);
  const rest = sum % 11;
  const check = rest < 2 ? 0 : 11 - rest;
  return check === Number(nif[8]);
}

/** Mensagem de erro do campo, ou `null` se estiver vazio (é opcional) ou for válido. */
export function nifError(value: string): string | null {
  if (!value.trim()) return null;
  if (!/^\d{9}$/.test(cleanNif(value))) return 'O NIF tem de ter 9 algarismos.';
  return isValidNif(value) ? null : 'Este NIF não é válido. Confirma os algarismos.';
}
