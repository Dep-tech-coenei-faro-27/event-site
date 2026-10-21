import { Link } from "react-router-dom";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";
import SystemState from "./SystemState";

/** `ui-ux/conta/link-expirado`: a ligação de verificação ou de recuperação expirou ou já foi usada. */
export default function LinkExpired() {
  useBodyPage("estado", "system-state-page system-state-page--warning");
  usePageMeta("Ligação expirada · ENEI 2027", "Esta ligação já não está disponível. Pede uma nova.");
  return (
    <SystemState
      icon={
        <>
          <path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1" />
          <path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1M12 8v4l2 1" />
        </>
      }
      kicker="Ligação inválida"
      title="Esta ligação já não está disponível."
      lead="A ligação expirou ou já foi utilizada. Pede uma nova para continuares a verificação do email ou a recuperação da conta."
      actions={
        <>
          <Link className="btn btn--primary" to="/conta/recuperar">
            Pedir nova ligação
          </Link>
          <Link className="btn btn--secondary" to="/conta">
            Voltar ao início de sessão
          </Link>
        </>
      }
      note="Usa sempre a ligação mais recente. As anteriores deixam de funcionar quando é feito um novo pedido."
      detail={{
        code: "422",
        heading: "A tua conta continua protegida.",
        text: "Nenhuma palavra-passe ou definição foi alterada através desta ligação.",
        facts: [
          { label: "Código", value: "422" },
          { label: "Conta", value: "Sem alterações" },
          { label: "Próximo passo", value: "Pedir nova ligação" },
        ],
      }}
    />
  );
}
