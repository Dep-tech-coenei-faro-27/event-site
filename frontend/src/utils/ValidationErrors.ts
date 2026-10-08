// Formato dos erros 422 da API:
// { "detail": [{ "type", "loc", "msg", "ctx": { "rules": [...] } }] }
// Nunca usamos `msg` (vem em inglês) nem mostramos valores enviados.

type ValidationItem = {
  type?: string;
  loc?: (string | number)[];
  ctx?: { rules?: string[] };
};

const passwordRules: Record<string, string> = {
  too_long: "A palavra-passe é demasiado longa (máximo de 200 caracteres).",
  missing_uppercase: "A palavra-passe tem de incluir uma letra maiúscula.",
  missing_digit: "A palavra-passe tem de incluir um número.",
  missing_symbol: "A palavra-passe tem de incluir um símbolo.",
};

const nameRules: Record<string, string> = {
  blank: "O nome não pode estar vazio.",
  invalid_characters: "O nome contém caracteres não permitidos.",
  no_letter: "O nome tem de incluir pelo menos uma letra.",
};

function messagesFor(item: ValidationItem): string[] {
  const field = item.loc?.[item.loc.length - 1];
  const rules = item.ctx?.rules ?? [];

  switch (item.type) {
    case "password_invalid":
      return rules.map((r) => passwordRules[r] ?? "A palavra-passe não é válida.");
    case "name_invalid":
      return rules.map((r) => nameRules[r] ?? "O nome não é válido.");
    case "email_not_ascii":
      return ["O email só pode conter caracteres ASCII (sem acentos)."];
    case "string_too_short":
      if (field === "password") return ["A palavra-passe tem de ter pelo menos 8 caracteres."];
      if (field === "name") return ["O nome não pode estar vazio."];
      break;
    case "string_too_long":
      if (field === "password") return ["A palavra-passe pode ter no máximo 200 caracteres."];
      if (field === "name") return ["O nome pode ter no máximo 255 caracteres."];
      break;
    case "missing":
      return ["Preenche todos os campos."];
  }

  if (field === "email") return ["Indica um email válido."];
  return [];
}

/** Converte `detail` de um 422 em mensagens claras, sem repetições. */
export function validationMessages(detail: unknown): string[] {
  if (!Array.isArray(detail)) return [];
  const all = (detail as ValidationItem[]).flatMap(messagesFor);
  return [...new Set(all)];
}