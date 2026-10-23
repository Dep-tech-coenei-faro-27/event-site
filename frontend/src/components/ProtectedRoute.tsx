import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../utils/useAuth';
import { loadErrorMessage } from '../utils/loadError';
import PageStatus from './PageStatus';

// O espaço de cima deixa o estado fora da barra de topo fixa.
const BELOW_TOPBAR = 'mx-auto max-w-[720px] px-5 pb-8 pt-[calc(64px+32px)] md:pt-[calc(76px+32px)]';

export default function ProtectedRoute() {
  const { user, loading, error, retry } = useAuth();
  const location = useLocation();

  if (loading) return <PageStatus state="loading" className={BELOW_TOPBAR} />;

  // Não se sabe se há sessão (rede, 5xx, 429): não é «sem sessão», por isso não vai ao login.
  if (!user && error) {
    return (
      <div className={BELOW_TOPBAR}>
        <PageStatus
          state="error"
          titleLevel={1}
          title="Não foi possível confirmar a tua sessão."
          message={loadErrorMessage(error)}
          onRetry={() => void retry()}
        />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/conta" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
