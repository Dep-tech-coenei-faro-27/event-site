import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { getAccount } from "../../payments/api";
import type { Account } from "../../payments/types";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";

/** Pagamento confirmado (`ui-ux/bilhetes/checkout/sucesso`). Os dados vêm da conta, por isso resiste a um refresh. */
export default function CheckoutSuccess() {
  useBodyPage("checkout", "payment-result-page");
  usePageMeta("Pagamento confirmado · ENEI 2027", "O teu lugar no ENEI 2027 está garantido.");

  const [account, setAccount] = useState<Account | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    let active = true;
    getAccount()
      .then((result) => active && setAccount(result))
      .catch(() => undefined)
      .finally(() => active && setDone(true));
    return () => {
      active = false;
    };
  }, []);

  // Quem chega aqui sem bilhete (endereço escrito à mão) volta aos bilhetes.
  if (done && !account?.ticket) return <Navigate to="/bilhetes" replace />;

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
            <span>{account?.ticket?.tier_name ?? "Bilhete"}</span>
            <strong>{account?.ticket?.reference ?? "…"}</strong>
          </div>
          <Link className="btn btn--primary" to="/perfil">
            Ver o meu bilhete
          </Link>
        </article>
      </div>
    </div>
  );
}
