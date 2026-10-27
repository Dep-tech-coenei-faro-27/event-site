import { createContext } from 'react';

export interface User {
  id: number | string;
  name: string;
  email: string;
  role: 'user' | 'admin';
  is_verified: boolean;
  /** Contacto opcional da conta (Dados pessoais). */
  phone?: string | null;
  qr_code: string | null;
  /** O bilhete emitido (de GET /users/me); `null` enquanto não há compra confirmada. */
  ticket?: { reference: string; tier: string; tier_name: string; holder_name: string; paid_at: string | null } | null;
  /** Um pagamento à espera de ser aprovado ou terminado pelo fornecedor. */
  pending_payment?: { reference: string; tier: string; tier_name: string; amount_cents: number; expires_at: string } | null;
  /** Um pagamento que chegou mas não pôde ter bilhete: vai ser reembolsado. */
  refund_due?: { reference: string; amount_cents: number } | null;
}

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  /**
   * A última verificação da sessão falhou sem ser por um 401 (rede, 5xx, 429). Com `user` a `null`
   * não se sabe se há sessão: mostra-se o erro com «Tentar novamente», sem ir ao login.
   */
  error: unknown;
  refresh: () => Promise<void>;
  /** Volta a verificar a sessão, passando por `loading`. */
  retry: () => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);