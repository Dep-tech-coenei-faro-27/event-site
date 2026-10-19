import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import mbwayLogo from "../../assets/mbway-logo.svg";
import { getAccount } from "../../payments/api";
import { loadReference, saveReference } from "../../payments/reference";
import { parseServerDate } from "../../payments/time";
import { usePaymentPolling } from "../../payments/usePaymentPolling";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";

/**
 * Espera do pagamento (`ui-ux/bilhetes/checkout/aguardar`). Pergunta ao servidor pelo estado de 2 em
 * 2 segundos (`usePaymentPolling`) e leva ao sucesso ou ao erro quando o pagamento termina. Depois de
 * recarregar a página, a referência continua guardada; sem ela, retoma-se pela conta.
 */
export default function CheckoutWaiting() {
  useBodyPage("checkout", "payment-result-page");
  usePageMeta("A aguardar o pagamento · ENEI 2027", "Confirma o pagamento na aplicação MB WAY.");

  const navigate = useNavigate();
  const [reference, setReference] = useState<string | null>(() => loadReference());
  const [resumeChecked, setResumeChecked] = useState(reference !== null);
  const [nothingToWatch, setNothingToWatch] = useState(false);

  // Sem referência guardada (outro dispositivo, outro separador): retoma pelo pagamento à espera da conta.
  useEffect(() => {
    if (reference) return;
    let active = true;
    getAccount()
      .then((account) => {
        if (!active) return;
        if (account.ticket) navigate("/bilhetes/checkout/sucesso", { replace: true });
        else if (account.pending_payment) {
          saveReference(account.pending_payment.reference);
          setReference(account.pending_payment.reference);
        } else setNothingToWatch(true);
      })
      .catch(() => active && setNothingToWatch(true))
      .finally(() => active && setResumeChecked(true));
    return () => {
      active = false;
    };
  }, [reference, navigate]);

  const watch = usePaymentPolling(reference);
  const { phase, transaction } = watch;

  // O pagamento terminou: sucesso ou erro (o `usePaymentPolling` apaga a referência guardada).
  useEffect(() => {
    if (phase === "confirmed") {
      navigate("/bilhetes/checkout/sucesso", { replace: true });
    } else if (["failed", "expired", "refund_due", "refunded", "not-found", "error"].includes(phase)) {
      navigate("/bilhetes/checkout/erro", {
        replace: true,
        state: { phase, accountChecked: watch.accountChecked },
      });
    }
  }, [phase, watch.accountChecked, navigate]);

  if (resumeChecked && nothingToWatch) return <Navigate to="/bilhetes/checkout" replace />;

  const confirming = phase === "confirming";

  return (
    <div className="payment-result-main">
      <div className="payment-result-shell">
        <article className="payment-status payment-status--waiting" aria-labelledby="status-title" aria-live="polite">
          <div className="payment-status__visuals">
            <div className="payment-status__icon" aria-hidden="true">
              <span className="payment-spinner"></span>
            </div>
            <img className="payment-result-mbway" src={mbwayLogo} alt="MB Way" />
          </div>
          <span className="payment-status__tag">{confirming ? "AINDA A CONFIRMAR" : "A AGUARDAR"}</span>
          <h1 id="status-title">Confirma no MB Way</h1>
          <p>
            {confirming
              ? "Ainda estamos a confirmar o pagamento. Se ainda não aprovaste, aprova-o agora na aplicação MB Way; o teu lugar continua reservado."
              : "Enviámos um pedido para o teu telemóvel. Confirma o pagamento na aplicação MB Way."}
          </p>
          {watch.connectionLost && (
            <p role="status">Perdemos a ligação. Não fechámos o pagamento: estamos a tentar outra vez.</p>
          )}
          <div className="payment-status__meta">
            <span>Referência</span>
            <strong>{transaction?.reference ?? reference ?? "…"}</strong>
          </div>
          <ExpiryNote expiresAt={transaction?.expires_at ?? null} confirming={confirming} />
          <Link className="payment-result-help" to="/perfil">
            Ver a minha conta
          </Link>
        </article>
      </div>
    </div>
  );
}

/** «O pedido expira dentro de N min»: só orienta, o estado verdadeiro vem sempre do servidor. */
function ExpiryNote({ expiresAt, confirming }: { expiresAt: string | null; confirming: boolean }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 5000);
    return () => window.clearInterval(timer);
  }, []);
  if (confirming || !expiresAt) return <small>O pedido expira dentro de alguns minutos.</small>;
  const minutes = Math.max(1, Math.ceil((parseServerDate(expiresAt) - now) / 60000));
  return <small>O pedido expira dentro de {minutes} {minutes === 1 ? "minuto" : "minutos"}.</small>;
}
