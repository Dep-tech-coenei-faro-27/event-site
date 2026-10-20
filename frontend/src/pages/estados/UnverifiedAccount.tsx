import { useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { http } from "../../utils/http";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";
import SystemState from "./SystemState";

/**
 * `ui-ux/conta/por-verificar`: a conta existe mas o email ainda não foi confirmado (403). O email
 * vem de quem leva para aqui (`location.state.email` ou `?email=`); sem ele não se pode reenviar.
 */
export default function UnverifiedAccount() {
  useBodyPage("estado", "system-state-page system-state-page--warning");
  usePageMeta("Conta por verificar · ENEI 2027", "Confirma o teu email para continuares.");

  const [search] = useSearchParams();
  const stateEmail = (useLocation().state as { email?: string } | null)?.email;
  const email = stateEmail ?? search.get("email") ?? "";
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "failed">("idle");

  async function resend() {
    setStatus("sending");
    try {
      await http("/auth/resend-verification-email", { method: "POST", body: { email } });
      setStatus("sent");
    } catch {
      setStatus("failed");
    }
  }

  return (
    <SystemState
      icon={
        <>
          <rect x="3" y="5" width="18" height="14" rx="1" />
          <path d="m4 7 8 6 8-6M18 15v3M18 21v.01" />
        </>
      }
      kicker="Conta por verificar"
      title="Confirma o teu email para continuar."
      lead={
        <>
          Enviámos uma ligação para {email ? <strong>{email}</strong> : "o teu email"}. Abre o email e confirma o
          endereço para ativares a conta.
        </>
      }
      actions={
        <>
          {email && (
            <button className="btn btn--primary" type="button" onClick={resend} disabled={status === "sending" || status === "sent"}>
              {status === "sent" ? "Email reenviado" : status === "sending" ? "A enviar…" : "Reenviar email"}
            </button>
          )}
          <Link className={`btn ${email ? "btn--secondary" : "btn--primary"}`} to="/conta/criar">
            Corrigir endereço
          </Link>
        </>
      }
      note={
        status === "failed"
          ? "Não foi possível reenviar agora. Espera um pouco e tenta outra vez."
          : "Verifica também a pasta de spam. Por segurança, a ligação de confirmação só pode ser utilizada uma vez."
      }
      detail={{
        code: "EMAIL",
        codeIsLabel: true,
        heading: "A confirmação protege a tua conta.",
        text: "Depois de confirmares o email, regressa à área de participante para completares o perfil.",
        facts: [
          { label: "Estado", value: "Confirmação pendente" },
          { label: "Código API", value: "403" },
          { label: "Próximo passo", value: "Abrir o email" },
        ],
      }}
    />
  );
}
