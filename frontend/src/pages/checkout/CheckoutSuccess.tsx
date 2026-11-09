import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import PageStatus from "../../components/PageStatus";
import { getAccount } from "../../payments/api";
import type { Account } from "../../payments/types";
import { isUnauthorized, loadErrorMessage } from "../../utils/loadError";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";

/** Pagamento confirmado (`ui-ux/bilhetes/checkout/sucesso`). Os dados vêm da conta, por isso resiste a um refresh. */
export default function CheckoutSuccess() {
  useBodyPage("checkout", "payment-result-page");
  usePageMeta("Pagamento confirmado · ENEI 2027", "O teu lugar no ENEI 2027 está garantido.");

  const navigate = useNavigate();
  const location = useLocation();
  const [account, setAccount] = useState<Account | null>(null);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getAccount({ signal: controller.signal })
      .then((result) => setAccount(result))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        // Sem sessão: entra e volta aqui. Outra falha não quer dizer «sem bilhete».
        if (isUnauthorized(error)) navigate("/conta", { replace: true, state: { from: location } });
        else setLoadError(error);
      });
    return () => controller.abort();
    // `location` só serve para voltar aqui depois do login; não volta a pedir a conta.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, navigate]);

  const retry = () => {
    setLoadError(null);
    setAttempt((n) => n + 1);
  };

  if (!account) {
    return (
      <div className="payment-result-main">
        <div className="payment-result-shell">
          {loadError === null ? (
            <PageStatus state="loading" message="A carregar o teu bilhete…" />
          ) : (
            <PageStatus
              state="error"
              titleLevel={1}
              title="Não conseguimos confirmar o teu bilhete."
              message={`${loadErrorMessage(loadError)} Se o pagamento foi aprovado, o bilhete não se perde.`}
              onRetry={retry}
            />
          )}
        </div>
      </div>
    );
  }

  // Quem chega aqui sem bilhete (endereço escrito à mão) volta aos bilhetes.
  if (!account.ticket) return <Navigate to="/bilhetes" replace />;

  return (
    <div className="payment-result-main">
      <div className="payment-result-shell">
        <article className="payment-status payment-status--success" aria-labelledby="status-title">
          <div className="payment-status__icon" aria-hidden="true">
            ✓
          </div>
          <span className="payment-status__tag">PAGAMENTO CONFIRMADO</span>
          <h1 id="status-title">O teu lugar está garantido.</h1>
          <p>O pagamento foi concluído. O teu bilhete e o código QR estão na tua área pessoal.</p>
          <div className="payment-status__meta">
            <span>{account.ticket.tier_name}</span>
            <strong>{account.ticket.reference}</strong>
          </div>
          <Link className="btn btn--primary" to="/perfil">
            Ver o meu bilhete
          </Link>
        </article>
      </div>
    </div>
  );
}
