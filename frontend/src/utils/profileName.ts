import { ApiError } from "./http";
import { retryAfterMessage } from "./RetryAfter";
import { nameRules, validationErrorsByField, validationMessages } from "./ValidationErrors";

export const NAME_MAX_LENGTH = 255;

// As mesmas categorias Unicode que o backend recusa (app/core/validators.py).
const INVISIBLE_OR_CONTROL = /[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}]/u;
const LETTER = /\p{L}/u;

/**
 * Erros do nome antes de o enviar, com as regras do servidor (`validate_name` e
 * `Field(min_length=1, max_length=255)`): o tamanho conta-se em caracteres Unicode,
 * como no Python, e sobre o valor já sem espaços nas pontas, que é o que se envia.
 */
export function nameErrors(raw: string): string[] {
  const name = raw.trim();

  if (!name) return [nameRules.blank];
  if (Array.from(name).length > NAME_MAX_LENGTH) {
    return [`O nome pode ter no máximo ${NAME_MAX_LENGTH} caracteres.`];
  }

  const errors: string[] = [];
  if (INVISIBLE_OR_CONTROL.test(name) || name.includes("<") || name.includes(">")) {
    errors.push(nameRules.invalid_characters);
  }
  if (!LETTER.test(name)) errors.push(nameRules.no_letter);
  return errors;
}

export type ProfileSaveError = { name?: string[]; form?: string };

/** Onde e como mostrar a falha de `PUT /api/users/me`. */
export function profileSaveError(err: unknown): ProfileSaveError {
  if (!(err instanceof ApiError)) return { form: "Não foi possível contactar o servidor." };

  switch (err.status) {
    case 401:
      return { form: "A tua sessão terminou. Entra novamente." };
    case 403:
      return { form: "Confirma o teu email antes de alterares os dados." };
    case 422: {
      const name = validationErrorsByField(err.detail).name;
      if (name?.length) return { name };
      const messages = validationMessages(err.detail);
      return { form: messages.length ? messages.join(" ") : "Os dados não são válidos." };
    }
    case 429:
      return { form: retryAfterMessage(err.retryAfter, "Demasiados pedidos.") };
    default:
      return { form: "Não foi possível guardar. Tenta novamente." };
  }
}
