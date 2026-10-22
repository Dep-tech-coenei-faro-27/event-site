import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../utils/useAuth';

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Fundo azul-base: nevoa-azul dá 9,5:1 (o texto preto antigo dava 1,09:1). O espaço de cima
  // deixa o texto fora da barra de topo fixa.
  if (loading) {
    return (
      <div role="status" className="px-5 pb-8 pt-[calc(64px+32px)] text-nevoa-azul md:pt-[calc(76px+32px)]">
        A carregar…
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/conta" replace state={{ from: location }} />;
  }
  return <Outlet />;
}