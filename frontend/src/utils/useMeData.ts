import { createContext, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { User } from "./authContextValue";
import { isUnauthorized } from "./loadError";
import { getMe } from "./users";

export interface MeData {
  /** `GET /users/me`: traz o bilhete e os pagamentos, que o utilizador de `/auth/me` não tem. */
  me: User | null;
  /** Erro do último pedido; só se mostra enquanto não há dados (se já há, mantêm-se). */
  error: unknown;
  retry: () => void;
  /** Volta a pedir sem mostrar «a carregar»: a página mostra o que tem e atualiza quando chegar. */
  revalidate: () => void;
}

/** Os dados de `/users/me` que a moldura da área pessoal guarda entre separadores. */
export const MeContext = createContext<MeData | null>(null);

export function useMeData(enabled = true): MeData {
  // `navigate` muda a cada mudança de rota: fica numa ref para `load` ser estável e o pedido não se repetir ao mudar de separador.
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  useEffect(() => {
    navigateRef.current = navigate;
  }, [navigate]);
  const [me, setMe] = useState<User | null>(null);
  const [error, setError] = useState<unknown>(null);
  const inflight = useRef<AbortController | null>(null);

  const load = useCallback(() => {
    if (inflight.current) return;
    const controller = new AbortController();
    inflight.current = controller;
    getMe({ signal: controller.signal })
      .then((data) => {
        if (controller.signal.aborted) return;
        setMe(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        if (isUnauthorized(err)) navigateRef.current("/conta?sessao=terminada", { replace: true });
        else setError(err);
      })
      .finally(() => {
        if (inflight.current === controller) inflight.current = null;
      });
  }, []);

  useEffect(() => {
    if (!enabled) return;
    load();
    return () => {
      inflight.current?.abort();
      inflight.current = null;
    };
  }, [enabled, load]);

  const retry = useCallback(() => {
    setError(null);
    load();
  }, [load]);

  return { me, error, retry, revalidate: load };
}
