import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { http, setUnauthorizedHandler } from './http';
import { AuthContext, type User } from './authContextValue';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Usado depois do login para atualizar o utilizador
  const refresh = useCallback(async () => {
    try {
      setUser(await http<User>('/auth/me'));
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Verificação inicial da sessão (GET /api/auth/me -> 401 sem sessão)
  useEffect(() => {
    let cancelled = false;
    http<User>('/auth/me')
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 401 em qualquer pedido privado: limpa estado e vai ao login
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      navigate('/conta', { replace: true });
    });
  }, [navigate]);

  const logout = useCallback(async () => {
    try {
      await http('/auth/logout', { method: 'POST' });
    } catch {
      // a API responde 200 mesmo sem sessão; se falhar a rede, limpamos na mesma
    } finally {
      setUser(null);
      navigate('/conta', { replace: true });
    }
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}