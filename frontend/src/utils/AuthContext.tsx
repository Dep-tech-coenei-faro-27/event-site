import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { http, setUnauthorizedHandler } from './http';

export interface User {
  id: number | string; // ajusta ao tipo real do teu id
  name: string;
  email: string;
  role: 'user' | 'admin';
  is_verified: boolean;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // GET /api/auth/me -> 401 sem sessão
  const refresh = useCallback(async () => {
    try {
      setUser(await http<User>('/auth/me'));
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

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
    } finally {
      setUser(null); // limpa estado local
      navigate('/conta', { replace: true }); // redireciona
    }
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth tem de ser usado dentro de <AuthProvider>');
  return ctx;
}