import { Link } from "react-router-dom";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";
import SystemState from "./SystemState";

/** `ui-ux/conta/sessao-terminada`: a sessão acabou (401). */
export default function SessionEnded() {
  useBodyPage("estado", "system-state-page");
  usePageMeta("Sessão terminada · ENEI 2027", "A tua sessão terminou. Volta a entrar para continuares.");
  return (
    <SystemState
      icon={
        <>
          <path d="M10 17l5-5-5-5M15 12H3" />
          <path d="M13 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" />
        </>
      }
      kicker="Sessão terminada"
      title="A tua sessão terminou."
      lead="Terminámos a sessão por segurança ou porque esteve inativa durante algum tempo. Volta a entrar para continuares."
      actions={
        <>
          <Link className="btn btn--primary" to="/conta">
            Iniciar sessão novamente
          </Link>
          <Link className="btn btn--secondary" to="/">
            Voltar ao início
          </Link>
        </>
      }
      note="As alterações que já foram confirmadas continuam guardadas. Dados ainda não enviados poderão ter de ser preenchidos novamente."
      detail={{
        code: "401",
        heading: "É necessário autenticar novamente.",
        text: "Esta medida ajuda a impedir o acesso à conta quando deixas o dispositivo sem supervisão.",
        facts: [
          { label: "Código", value: "401" },
          { label: "Conta", value: "Protegida" },
          { label: "Próximo passo", value: "Iniciar sessão" },
        ],
      }}
    />
  );
}
