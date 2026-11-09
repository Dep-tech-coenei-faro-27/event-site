import { useContext } from 'react';
import { AuthContext, type AuthContextValue } from './authContextValue';

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth tem de ser usado dentro de <AuthProvider>');
  return ctx;
}