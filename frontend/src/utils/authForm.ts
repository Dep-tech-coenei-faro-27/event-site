import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./http";
import { retryAfterMessage } from "./RetryAfter";
import { validationErrorsByField } from "./ValidationErrors";

/** Erros de um formulário: por campo (`name` do input) e um aviso geral. */
export type FormErrors = { fields: Record<string, string[]>; message: string | null };

export const noErrors: FormErrors = { fields: {}, message: null };

export const formMessage = (message: string): FormErrors => ({ fields: {}, message });

export const NETWORK_MESSAGE =
  "Não foi possível contactar o servidor. Verifica a tua ligação e tenta novamente.";

/**
 * Os erros que todas as páginas de entrada tratam da mesma forma: rede em baixo, 422 por campo
 * (com as regras de `ctx.rules`), 429 com o tempo do `Retry-After` e 5xx. Os próprios de cada página
 * (401, 403, 409, 400) tratam-se antes de chegar aqui.
 */
export function formErrorsFrom(err: unknown, rateLimitText: string): FormErrors {
  if (!(err instanceof ApiError)) return formMessage(NETWORK_MESSAGE);
  if (err.status === 422) {
    const { _form, ...fields } = validationErrorsByField(err.detail);
    if (!Object.keys(fields).length && !_form) return formMessage("Verifica os dados do formulário.");
    return { fields, message: _form ? _form.join(" ") : null };
  }
  if (err.status === 429) return formMessage(retryAfterMessage(err.retryAfter, rateLimitText));
  if (err.status >= 500) return formMessage("Ocorreu um erro no servidor. Tenta novamente dentro de momentos.");
  return formMessage("Ocorreu um erro. Tenta novamente.");
}

/**
 * Estado de envio de um formulário de entrada: um pedido de cada vez (nem o duplo clique envia
 * duas vezes), os erros e o foco. Depois de um erro, o foco vai para o primeiro campo inválido
 * ou, se não houver, para o aviso (`alertRef`). O que a pessoa escreveu nunca se apaga.
 */
export function useAuthForm() {
  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<FormErrors>(noErrors);
  const [failures, setFailures] = useState(0);
  const inFlight = useRef(false);
  const formRef = useRef<HTMLFormElement>(null);
  const alertRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (!failures) return;
    const invalid = formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
    (invalid ?? alertRef.current)?.focus();
  }, [failures]);

  const fail = useCallback((next: FormErrors) => {
    setErrors(next);
    setFailures((count) => count + 1);
  }, []);

  const submit = useCallback(async (task: () => Promise<void>) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setErrors(noErrors);
    try {
      await task();
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }, []);

  return { pending, errors, fail, submit, formRef, alertRef };
}
