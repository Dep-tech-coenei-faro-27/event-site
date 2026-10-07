import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import Eyebrow from "../components/EyeBrow";
import PrimaryButton from "../components/PrimaryButton";
import SecondaryButton from "../components/SecundaryButton";

type Status =
  | "pending" // sem token: "Verifica o teu email" (texto do mockup)
  | "loading"
  | "success"
  | "invalid"
  | "rate_limited"
  | "error";

const points = [
  "Confirma o endereço de email.",
  "Regressa à área de participante.",
  "Completa o teu perfil.",
];

const iconProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  className: "size-[31px]",
};

function MailIcon() {
  return (
    <svg {...iconProps}>
      <rect x="3" y="5" width="18" height="14" rx="1" />
      <path d="m4 7 8 6 8-6M16 16l2 2 4-5" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5.5M12 16.5v.01" />
    </svg>
  );
}

// Botões com cantos de 2px e largura total, como no .auth-actions do CSS original
const actionClass = "w-full !rounded-[2px]";

// Títulos como no mockup (pesados)
const headingFont = "font-montserrat font-extrabold";

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const token = params.get("token");

  // Email mostrado no estado "pending". Vem do registo:
  // navigate("/conta/verificar", { state: { email } })
  const email = (location.state as { email?: string } | null)?.email;

  const [status, setStatus] = useState<Status>(token ? "loading" : "pending");
  const [showResendNote, setShowResendNote] = useState(false);
  // Evita enviar o pedido duas vezes (React StrictMode corre o efeito 2x em dev)
  const requested = useRef(false);

  useEffect(() => {
    if (!token || requested.current) return;
    requested.current = true;

    (async () => {
      try {
        const res = await fetch("/api/auth/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        if (res.ok) setStatus("success");
        else if (res.status === 400) setStatus("invalid");
        else if (res.status === 429) setStatus("rate_limited");
        else setStatus("error");
      } catch {
        setStatus("error");
      }
    })();
  }, [token]);

  const content: Record<
    Status,
    { icon: ReactNode; eyebrow: string; title: string; text: ReactNode }
  > = {
    pending: {
      icon: <MailIcon />,
      eyebrow: "VERIFICAÇÃO",
      title: "Verifica o teu email.",
      text: email ? (
        <>
          Enviámos uma ligação de confirmação para{" "}
          <strong className="text-white">{email}</strong>. Abre-a para ativares
          a conta.
        </>
      ) : (
        "Enviámos uma ligação de confirmação para o teu email. Abre-a para ativares a conta."
      ),
    },
    loading: {
      icon: <MailIcon />,
      eyebrow: "A_VERIFICAR",
      title: "A confirmar o teu email...",
      text: "Só demora um instante.",
    },
    success: {
      icon: <MailIcon />,
      eyebrow: "EMAIL_CONFIRMADO",
      title: "Conta confirmada.",
      text: "O teu email foi verificado com sucesso. Já podes entrar na tua conta ENEI.",
    },
    invalid: {
      icon: <AlertIcon />,
      eyebrow: "LINK_INVALIDO",
      title: "Este link já não é válido.",
      text: "O link expirou (vale 30 minutos) ou foi substituído por um mais recente. Se a tua palavra-passe mudou ou a conta foi recriada, o link antigo deixa de funcionar. Cria a conta novamente para receberes um novo email.",
    },
    rate_limited: {
      icon: <AlertIcon />,
      eyebrow: "DEMASIADAS_TENTATIVAS",
      title: "Tenta novamente mais tarde.",
      text: "Foram feitas demasiadas tentativas a partir desta ligação. Aguarda uns minutos e volta a abrir o link do email.",
    },
    error: {
      icon: <AlertIcon />,
      eyebrow: "ERRO",
      title: "Algo correu mal.",
      text: "Não foi possível confirmar o email. Verifica a ligação e tenta novamente.",
    },
  };

  const current = content[status];

  return (
    <div className="azulejo-bg min-h-screen bg-azul-base pt-16 font-poppins leading-[1.65] text-white min-[621px]:pt-[76px] max-[620px]:pb-[84px]">
      <main
        id="conteudo"
        className="relative overflow-hidden min-[621px]:min-h-[calc(100vh-76px)]"
      >
        <div
          aria-hidden="true"
          className="azulejo-bg pointer-events-none absolute inset-0 bg-acento-principal opacity-[0.025]"
        />

        <section className="relative z-[1] overflow-hidden pb-3 pt-[18px] min-[621px]:pb-6 min-[621px]:pt-[clamp(48px,7vw,92px)]">
          <div className="mx-auto grid w-[min(calc(100%-20px),1180px)] overflow-hidden rounded-[4px] border border-[rgba(26,178,255,0.42)] bg-azul-painel shadow-[0_18px_38px_-28px_rgba(0,0,0,0.95),0_8px_20px_-18px_rgba(26,178,255,0.28)] min-[621px]:w-[min(calc(100%-40px),1180px)] min-[901px]:min-h-[600px] min-[901px]:grid-cols-[minmax(300px,0.8fr)_minmax(0,1.2fr)]">
            <aside className="relative flex min-h-[310px] flex-col justify-between overflow-hidden border-b border-[rgba(26,178,255,0.42)] bg-[linear-gradient(150deg,rgba(26,178,255,0.2),transparent_58%)] bg-azul-superficie px-[22px] py-[30px] min-[621px]:min-h-[360px] min-[621px]:p-[clamp(38px,5vw,64px)] min-[901px]:border-b-0 min-[901px]:border-r">
              <img
                src="/assets/ENEI-logo.svg"
                alt=""
                aria-hidden="true"
                className="pointer-events-none absolute bottom-7 right-[34px] h-[206px] w-[86px] object-contain opacity-[0.07]"
              />
              <div className="relative">
                <Eyebrow text="EMAIL" />
                <h1
                  className={`max-w-[520px] text-[clamp(38px,5vw,64px)] leading-[1.06] tracking-[-0.045em] ${headingFont}`}
                >
                  Falta apenas um passo.
                </h1>
                <p className="mt-5 max-w-[720px] text-[17px] text-cinza-texto">
                  A confirmação mantém a tua conta segura e garante que recebes
                  a informação certa.
                </p>
              </div>
              <div className="relative mt-8 grid max-w-[390px] gap-2.5">
                {points.map((text, i) => (
                  <div
                    key={text}
                    className="grid min-h-[38px] grid-cols-[34px_1fr] items-center gap-3.5 text-sm text-cinza-texto"
                  >
                    <span className="grid size-[34px] place-items-center border border-[rgba(26,178,255,0.42)] font-montserrat text-[11px] font-bold text-acento-forte">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <p className="m-0 leading-[1.45]">{text}</p>
                  </div>
                ))}
              </div>
            </aside>

            {/* Card */}
            <div
              role="status"
              aria-live="polite"
              className="flex flex-col justify-center bg-[linear-gradient(145deg,rgba(26,178,255,0.035),transparent_45%)] bg-azul-painel px-[22px] py-[30px] min-[621px]:p-[clamp(38px,6vw,74px)]"
            >
              <div
                aria-hidden="true"
                className="mb-6 grid size-16 place-items-center border border-[rgba(26,178,255,0.42)] bg-[rgba(26,178,255,0.08)] text-acento-forte"
              >
                {current.icon}
              </div>

              <Eyebrow text={current.eyebrow} />
              <h2
                className={`text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em] ${headingFont}`}
              >
                {current.title}
              </h2>
              <p className="mt-3.5 max-w-[560px] text-cinza-texto">
                {current.text}
              </p>

              {status !== "loading" && (
                <div className="mt-7 grid gap-2.5">
                  {status === "pending" && (
                    <>
                      <PrimaryButton
                        text="Abrir a minha conta"
                        className={actionClass}
                        onClick={() => navigate("/conta/entrar")}
                      />
                      <SecondaryButton
                        text="Reenviar email"
                        className={actionClass}
                        onClick={() => setShowResendNote(true)}
                      />
                    </>
                  )}

                  {status === "success" && (
                    <PrimaryButton
                      text="Entrar na conta"
                      className={actionClass}
                      onClick={() => navigate("/conta/entrar")}
                    />
                  )}

                  {status === "invalid" && (
                    <>
                      <PrimaryButton
                        text="Criar conta"
                        className={actionClass}
                        onClick={() => navigate("/conta/criar")}
                      />
                      <SecondaryButton
                        text="Entrar"
                        className={actionClass}
                        onClick={() => navigate("/conta/entrar")}
                      />
                    </>
                  )}

                  {(status === "rate_limited" || status === "error") && (
                    <SecondaryButton
                      text="Tentar novamente"
                      className={actionClass}
                      onClick={() => window.location.reload()}
                    />
                  )}
                </div>
              )}

              {status === "pending" && showResendNote && (
                <p className="mt-[18px] border-l-[3px] border-acento-principal bg-[rgba(26,178,255,0.07)] px-3.5 py-3 text-xs text-gelo">
                  Ainda não é possível reenviar o email a partir daqui. Se não o
                  recebeste, volta a criar a conta com o mesmo email para
                  receberes uma nova ligação.
                </p>
              )}

              {status !== "success" && (
                <p className="mt-6 text-center text-sm text-cinza-texto">
                  <Link
                    to="/conta/entrar"
                    className="font-semibold text-acento-forte"
                  >
                    ← Voltar ao início de sessão
                  </Link>
                </p>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}