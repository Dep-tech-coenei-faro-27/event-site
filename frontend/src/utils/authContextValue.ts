import { createContext } from 'react';

export interface User {
  id: number | string;
  name: string;
  email: string;
  role: 'user' | 'admin';
  is_verified: boolean;
}

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);