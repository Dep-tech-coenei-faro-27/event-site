import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { http, setUnauthorizedHandler } from './http';
import { AuthContext, type User } from './authContextValue';
import { isUnauthorized } from './loadError';


export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const navigate = useNavigate();

  // GET /api/auth/me. Só um 401 quer dizer «sem sessão»; uma falha de rede, um 5xx ou um 429 não
  // dizem nada sobre a sessão: guardam o erro e mantêm o utilizador que já se conhecia.
  const check = useCallback(
    (signal?: AbortSignal) =>
      http<User>('/auth/me', { signal })
        .then((me) => {
          if (signal?.aborted) return;
          setUser(me);
          setError(null);
        })
        .catch((err: unknown) => {
          if (signal?.aborted) return;
          if (isUnauthorized(err)) setUser(null);
          setError(isUnauthorized(err) ? null : err);
        })
        .finally(() => {
          if (!signal?.aborted) setLoading(false);
        }),
    [],
  );

  // Usado depois do login e de guardar os dados para atualizar o utilizador
  const refresh = useCallback(() => check(), [check]);

  // Depois de uma falha: volta a «a carregar» e pergunta outra vez
  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    return check();
  }, [check]);

  // Verificação inicial da sessão (o pedido é cancelado se o provider sair)
  useEffect(() => {
    const controller = new AbortController();
    check(controller.signal);
    return () => controller.abort();
  }, [check]);

  // 401 em qualquer pedido privado: limpa estado e vai ao login
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      navigate('/conta?sessao=terminada', { replace: true });
    });
    return () => {
      setUnauthorizedHandler(() => { });
    };
  }, [navigate]);

  const logout = useCallback(async () => {
    try {
      await http('/auth/logout', { method: 'POST' });
    } catch {
      // a API responde 200 mesmo sem sessão; se falhar a rede, limpamos na mesma
    } finally {
      setUser(null);
      setError(null);
      navigate('/conta', { replace: true });
    }
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ user, loading, error, refresh, retry, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
