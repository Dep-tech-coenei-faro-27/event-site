import { ApiError } from "./http";
import { retryAfterMessage } from "./RetryAfter";
import { validationMessages } from "./ValidationErrors";

/** Regras da nova palavra-passe (as do backend) e mensagens de `PUT /api/auth/password`. */
export const passwordRules = [
  { label: "Mínimo de 8 caracteres", test: (p: string) => p.length >= 8 },
  { label: "Uma letra maiúscula", test: (p: string) => /[A-Z]/.test(p) },
  { label: "Um número", test: (p: string) => /\d/.test(p) },
  { label: "Um símbolo", test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

// Mesmo limite do backend (bcrypt só usa os primeiros 72 bytes).
export const byteLength = (s: string) => new TextEncoder().encode(s).length;

/** Erro do formulário antes de pedir à API, ou `null` se estiver bem. */
export function passwordFormError(current: string, next: string, confirm: string): string | null {
  if (!passwordRules.every((rule) => rule.test(next))) return "A nova palavra-passe não cumpre todos os requisitos.";
  if (byteLength(next) > 72) return "A palavra-passe é demasiado longa.";
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
