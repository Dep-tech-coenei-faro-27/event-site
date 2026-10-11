import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../utils/useAuth';

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <div className="p-8 text-black">A carregar...</div>;

  if (!user) {
    return <Navigate to="/conta" replace state={{ from: location }} />;
  }
  return <Outlet />;
}