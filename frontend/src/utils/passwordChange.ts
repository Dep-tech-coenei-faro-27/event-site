import { ApiError } from "./http";
import { retryAfterMessage } from "./RetryAfter";
import { validationMessages } from "./ValidationErrors";

/**
 * Regras da palavra-passe, as mesmas de `validate_password` (backend/app/core/security.py) e do
 * `min_length=8` dos schemas. `code` é o nome que o backend usa em `ctx.rules` (o mínimo vem como
 * `string_too_short`). Como em Python, os caracteres contam-se por code point e as maiúsculas e os
 * algarismos não se limitam ao ASCII (os algarismos em expoente, como «²», ficam de fora).
 */
export const passwordRules = [
  { code: "too_short", label: "Mínimo de 8 caracteres", test: (p: string) => [...p].length >= 8 },
  { code: "missing_uppercase", label: "Uma letra maiúscula", test: (p: string) => /\p{Uppercase}/u.test(p) },
  { code: "missing_digit", label: "Um número", test: (p: string) => /\p{Nd}/u.test(p) },
  { code: "missing_symbol", label: "Um símbolo", test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

// Mesmo limite do backend (bcrypt só usa os primeiros 72 bytes).
export const byteLength = (s: string) => new TextEncoder().encode(s).length;

/** Os `ctx.rules` que o backend devolveria para `password`, pela mesma ordem. */
export function failedPasswordRules(password: string): string[] {
  const failed = byteLength(password) > 72 ? ["too_long"] : [];
  for (const rule of passwordRules) {
    if (rule.code !== "too_short" && !rule.test(password)) failed.push(rule.code);
  }
  return failed;
}

/** Erro da nova palavra-passe antes de pedir à API, ou `null` se cumpre as regras. */
export function newPasswordError(password: string): string | null {
  if (!passwordRules.every((rule) => rule.test(password))) return "A palavra-passe não cumpre todos os requisitos.";
  if (byteLength(password) > 72) return "A palavra-passe é demasiado longa.";
  return null;
}

/** Erro do formulário antes de pedir à API, ou `null` se estiver bem. */
export function passwordFormError(current: string, next: string, confirm: string): string | null {
  const problem = newPasswordError(next);
  if (problem) return problem;
  if (next !== confirm) return "As palavras-passe não coincidem.";
  if (next === current) return "A nova palavra-passe tem de ser diferente da atual.";
  return null;
}

export function passwordChangeMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return "Não foi possível contactar o servidor.";

  switch (err.status) {
    case 400:
      return err.message.toLowerCase().includes("different from your current")
        ? "A nova palavra-passe tem de ser diferente da atual."
        : "Não foi possível alterar a palavra-passe. Tenta novamente.";
    case 401:
      return err.message === "Current password is incorrect"
        ? "A palavra-passe atual está incorreta."
        : "A tua sessão terminou. Entra novamente.";
    case 403:
      return "Confirma o teu email antes de alterares a palavra-passe.";
    case 422: {
      const messages = validationMessages(err.detail);
      return messages.length ? messages.join(" ") : "A palavra-passe não cumpre os requisitos de segurança.";
    }
    case 429:
      return retryAfterMessage(err.retryAfter, "Demasiadas alterações de palavra-passe.");
    default:
      return "Ocorreu um erro. Tenta novamente.";
  }
}
