import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";
import SystemState from "./SystemState";

const DEFAULT_WAIT_SECONDS = 15 * 60;

/** Segundos de espera: o `Retry-After` que o servidor deu (em `location.state`), ou 15 minutos. */
function waitFrom(state: unknown): number {
  const seconds = (state as { retryAfterSeconds?: number } | null)?.retryAfterSeconds;
  return typeof seconds === "number" && seconds > 0 ? Math.ceil(seconds) : DEFAULT_WAIT_SECONDS;
}

const clock = (seconds: number) =>
  `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

/** `ui-ux/conta/demasiadas-tentativas`: 429, com o contador até se poder tentar outra vez. */
export default function TooManyAttempts() {
  useBodyPage("estado", "system-state-page system-state-page--danger");
  usePageMeta("Demasiadas tentativas · ENEI 2027", "Aguarda um pouco antes de voltares a tentar.");

  const navigate = useNavigate();
  const { state } = useLocation();
  const [remaining, setRemaining] = useState(() => waitFrom(state));

  useEffect(() => {
    if (remaining <= 0) return;
    const timer = window.setTimeout(() => setRemaining((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [remaining]);

  const ready = remaining <= 0;

  return (
    <SystemState
      icon={
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2M8 3 5-2 5 2" />
        </>
      }
      kicker="Acesso temporariamente limitado"
      title="Precisamos de fazer uma pausa."
      lead="Foram feitas várias tentativas num curto período. Para proteger a tua conta, aguarda antes de voltares a tentar."
      actions={
        <>
          <button className="btn btn--primary" type="button" disabled={!ready} onClick={() => navigate("/conta")}>
            {ready ? "Tentar novamente" : "Aguardar para tentar"}
          </button>
          <Link className="btn btn--secondary" to="/informacao-ajuda">
            Pedir ajuda
          </Link>
        </>
      }
      note="Não atualizes repetidamente a página. O contador continua até ser seguro fazer uma nova tentativa."
      detail={{
        code: "429",
        heading: "Volta a tentar quando o tempo terminar.",
        text: "O limite evita tentativas automáticas e não altera os dados da tua conta.",
        extra: (
          <div className="system-state-countdown">
            <span>{ready ? "Já podes voltar a tentar" : "Nova tentativa disponível em"}</span>
            <strong aria-live="polite">{clock(Math.max(remaining, 0))}</strong>
          </div>
        ),
        facts: [
          { label: "Código", value: "429" },
          { label: "Conta", value: "Sem alterações" },
          { label: "Próximo passo", value: "Aguardar" },
        ],
      }}
    />
  );
}
