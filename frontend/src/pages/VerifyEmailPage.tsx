import { useEffect, useRef, useState, type ReactNode, type SyntheticEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import AuthLayout, { AuthEyebrow, AuthStateIcon } from "../components/auth/AuthLayout";
import AuthField from "../components/auth/AuthField";
import AuthAlert from "../components/auth/AuthAlert";
import { usePageMeta } from "../utils/usePageMeta";
import { formErrorsFrom, formMessage, useAuthForm } from "../utils/authForm";
import { http, ApiError } from "../utils/http";
import { retryAfterSeconds } from "../payments/errors";

type Status =
  | "pending" // sem token: "Verifica o teu email" (texto do mockup)
  | "loading"
  | "success"
  | "error";

const points = [
  "Confirma o endereço de email.",
  "Regressa à área de participante.",
  "Completa o teu perfil.",
];

const mailIcon = (
  <>
    <rect x="3" y="5" width="18" height="14" rx="1" />
    <path d="m4 7 8 6 8-6M16 16l2 2 4-5" />
  </>
);

const alertIcon = (
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5.5M12 16.5v.01" />
  </>
);

export default function VerifyEmailPage() {
  usePageMeta("Verificar email · ENEI 2027", "Verificação de email da conta ENEI 2027.");

  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const token = params.get("token");

  // Email mostrado no estado "pending". Vem do registo:
  // navigate("/conta/verificar", { state: { email, registered: true } })
  const routeState = location.state as { email?: string; registered?: boolean } | null;
  const email = routeState?.email;

  const [status, setStatus] = useState<Status>(token ? "loading" : "pending");
  // Reenvio do email de verificação
  const [emailInput, setEmailInput] = useState("");
  const [resent, setResent] = useState(false);
  const { pending, errors, fail, submit, formRef, alertRef } = useAuthForm();
  // Evita enviar o pedido duas vezes (React StrictMode corre o efeito 2x em dev)
  const requested = useRef(false);

  useEffect(() => {
    if (!token || requested.current) return;
    requested.current = true;

    (async () => {
      try {
        await http("/auth/verify-email", {
          method: "POST",
          body: { token },
        });
        setStatus("success");
      } catch (err) {
        if (err instanceof ApiError && err.status === 400) {
          // Ligação expirada, já usada ou substituída: a página própria deixa pedir um novo email.
          navigate("/conta/link-expirado", { replace: true, state: { link: "verificacao" } });
        } else if (err instanceof ApiError && err.status === 429) {
          navigate("/conta/demasiadas-tentativas", {
            replace: true,
            state: { retryAfterSeconds: retryAfterSeconds(err.retryAfter) },
          });
        } else {
          setStatus("error");
        }
      }
    })();
  }, [token, navigate]);

  const handleResend = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    const target = (email ?? emailInput).trim();
    if (!target) {
      fail({ fields: { email: ["Indica o email da conta."] }, message: null });
      return;
    }

    void submit(async () => {
      setResent(false);
      try {
        await http("/auth/resend-verification-email", {
          method: "POST",
          body: { email: target },
        });
        // 200 → resposta sempre igual, exista a conta ou não
        setResent(true);
      } catch (err) {
        const next = formErrorsFrom(err, "Pediste demasiados reenvios.");
        // Com o email vindo do registo não há campo onde mostrar o erro: vai para o aviso.
        fail(email && next.fields.email ? formMessage(next.fields.email.join(" ")) : next);
      }
    });
  };

  const content: Record<Status, { icon: ReactNode; eyebrow: string; title: string; text: ReactNode }> = {
    pending: {
      icon: mailIcon,
      eyebrow: "VERIFICAÇÃO",
      title: routeState?.registered ? "Conta criada. Verifica o teu email." : "Verifica o teu email.",
      text: email ? (
        <>
          Enviámos uma ligação de confirmação para <strong>{email}</strong>. Abre-a para ativares a conta.
        </>
      ) : (
        "Enviámos uma ligação de confirmação para o teu email. Abre-a para ativares a conta."
      ),
    },
    loading: {
      icon: mailIcon,
      eyebrow: "A_VERIFICAR",
      title: "A confirmar o teu email…",
      text: "Só demora um instante.",
    },
    success: {
      icon: mailIcon,
      eyebrow: "EMAIL_CONFIRMADO",
      title: "Conta confirmada.",
      text: "O teu email foi verificado com sucesso. Já podes entrar na tua conta ENEI.",
    },
    error: {
      icon: alertIcon,
      eyebrow: "ERRO",
      title: "Algo correu mal.",
      text: "Não foi possível confirmar o email. Verifica a ligação e tenta novamente.",
    },
  };

  const current = content[status];

  return (
    <AuthLayout
      eyebrow="EMAIL"
      title="Falta apenas um passo."
      lead="A confirmação mantém a tua conta segura e garante que recebes a informação certa."
      points={points}
    >
      <div role="status" aria-live="polite">
        <AuthStateIcon>{current.icon}</AuthStateIcon>
        <AuthEyebrow text={current.eyebrow} />
        <h2>{current.title}</h2>
        <p className="auth-intro">{current.text}</p>
      </div>

      {status === "pending" && (
        <form ref={formRef} className="auth-actions" onSubmit={handleResend}>
          {!email && (
            <AuthField
              label="Email da conta"
              name="email"
              type="email"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              placeholder="nome@exemplo.pt"
              autoComplete="email"
              error={errors.fields.email}
            />
          )}
          <button className="btn btn--primary" type="button" onClick={() => navigate("/conta")}>
            Abrir a minha conta
          </button>
          <button className="btn btn--secondary" type="submit" disabled={pending} aria-busy={pending}>
            {pending ? "A enviar…" : "Reenviar email"}
          </button>
          <AuthAlert message={errors.message} alertRef={alertRef} />
          {resent && (
            <p role="status" className="auth-status">
              Se a conta estiver por verificar, enviámos um novo email de verificação.
            </p>
          )}
        </form>
      )}

      {status === "success" && (
        <div className="auth-actions">
          <button className="btn btn--primary" type="button" onClick={() => navigate("/perfil")}>
            Entrar na conta
          </button>
        </div>
      )}

      {status === "error" && (
        <div className="auth-actions">
          <button className="btn btn--secondary" type="button" onClick={() => window.location.reload()}>
            Tentar novamente
          </button>
        </div>
      )}

      {status !== "success" && (
        <p className="auth-switch">
          <Link className="auth-back" to="/conta">
            ← Voltar ao início de sessão
          </Link>
        </p>
      )}
    </AuthLayout>
  );
}
