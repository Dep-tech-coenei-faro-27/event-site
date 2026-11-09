import { Link, useLocation } from "react-router-dom";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";

type State = { phase?: string; accountChecked?: boolean } | null;

/**
 * O pagamento não terminou em bilhete (`ui-ux/bilhetes/checkout/erro`). O texto depende de como
 * acabou: recusado, expirado, a caminho de reembolso, referência desconhecida ou sem forma de saber.
 * «Sem cobrança» só se diz quando se conferiu a conta (um pagamento tardio ainda pode ter emitido bilhete).
 */
export default function CheckoutError() {
  useBodyPage("checkout", "payment-result-page");
  usePageMeta("Pagamento não concluído · ENEI 2027", "O pagamento não foi concluído.");

  const state = useLocation().state as State;
  const view = describe(state?.phase, state?.accountChecked !== false);

  return (
    <div className="payment-result-main">
      <div className="payment-result-shell">
        <article className="payment-status payment-status--error" aria-labelledby="status-title">
          <div className="payment-status__icon" aria-hidden="true">
            !
          </div>
          <span className="payment-status__tag">{view.tag}</span>
          <h1 id="status-title">{view.title}</h1>
          <p>{view.text}</p>
          <div className="payment-status__meta">
            <span>Estado</span>
            <strong>{view.status}</strong>
          </div>
          {view.retry ? (
            <Link className="btn btn--secondary" to="/bilhetes/checkout">
              Tentar novamente
            </Link>
          ) : (
            <Link className="btn btn--secondary" to="/perfil">
              Ver a minha conta
            </Link>
          )}
          <Link className="payment-result-help" to="/informacao-ajuda">
            Precisas de ajuda?
          </Link>
        </article>
      </div>
    </div>
  );
}

function describe(phase: string | undefined, accountChecked: boolean) {
  switch (phase) {
    case "refund_due":
    case "refunded":
      return {
        tag: "REEMBOLSO A CAMINHO",
        title: "O pagamento chegou, mas não conseguimos emitir o bilhete.",
        text: "O lugar já não estava disponível. Devolvemos o valor ao teu MB Way; não precisas de fazer nada.",
        status: "Reembolso a caminho",
        retry: false,
      };
    case "not-found":
      return {
        tag: "PAGAMENTO NÃO ENCONTRADO",
        title: "Não encontrámos este pagamento.",
        text: "A referência guardada não é desta conta ou já não existe. Vê na tua conta se tens um bilhete.",
        status: "Por confirmar",
        retry: false,
      };
    case "error":
      return {
        tag: "SEM RESPOSTA",
        title: "Não conseguimos ver o estado do pagamento.",
        text: "Antes de tentares outra vez, confirma na tua conta se o pagamento foi feito.",
        status: "Por confirmar",
        retry: false,
      };
    default:
      return {
        tag: "PAGAMENTO NÃO CONCLUÍDO",
        title: "Não foi possível pagar.",
        text: accountChecked
          ? "O pedido foi recusado ou expirou. Confirma o número e tenta novamente."
          : "O pedido foi recusado ou expirou, mas não conseguimos confirmar se houve cobrança. Vê a tua conta antes de tentares outra vez.",
        status: accountChecked ? "Sem cobrança" : "Por confirmar",
        retry: accountChecked,
      };
  }
}
