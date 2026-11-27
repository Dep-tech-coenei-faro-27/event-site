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

// Morada da fatura (pedida só com o NIF): rua, código postal «NNNN-NNN» e localidade.

/** Código postal português com o hífen (aceita-se sem ele). */
export const cleanPostalCode = (value: string) => {
  const code = value.trim();
  return /^\d{4}-?\d{3}$/.test(code) ? `${code.slice(0, 4)}-${code.slice(-3)}` : null;
};

const squash = (value: string) => value.trim().replace(/\s+/g, ' ');

export type BillingAddressFields = { street: string; postalCode: string; city: string };

/** Mensagem de erro de cada campo da morada, ou `null` se estiver certo. */
export function addressErrors({ street, postalCode, city }: BillingAddressFields) {
  return {
    street: squash(street).length < 5 ? 'Indica a rua e o número da porta.' : null,
    postalCode: cleanPostalCode(postalCode) ? null : 'Indica o código postal com 7 algarismos, por exemplo 8000-123.',
    city: squash(city).length < 2 ? 'Indica a localidade.' : null,
  };
}

export function cleanAddress({ street, postalCode, city }: BillingAddressFields) {
  return {
    billing_street: squash(street),
    billing_postal_code: cleanPostalCode(postalCode) ?? '',
    billing_city: squash(city),
  };
}
