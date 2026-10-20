import { createContext } from 'react';

export interface User {
  id: number | string;
  name: string;
  email: string;
  role: 'user' | 'admin';
  is_verified: boolean;
  course: string | null;
  qr_code: string | null;
  ticket_status?: 'none' | 'pending' | 'confirmed';
  payment_status?: 'pending' | 'paid' | 'failed' | null;
}

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);