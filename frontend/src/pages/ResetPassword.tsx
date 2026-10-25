import { useState, type SyntheticEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import AuthLayout, { AuthEyebrow, AuthStateIcon } from "../components/auth/AuthLayout";
import AuthField from "../components/auth/AuthField";
import AuthAlert from "../components/auth/AuthAlert";
import PasswordRules from "../components/PasswordRules";
import { usePageMeta } from "../utils/usePageMeta";
import { formErrorsFrom, formMessage, useAuthForm } from "../utils/authForm";
import { newPasswordError } from "../utils/passwordChange";
import { http, ApiError } from "../utils/http";

const points = [
  "Evita palavras-passe reutilizadas.",
  "Combina letras, números e símbolos.",
  "Guarda-a num gestor de palavras-passe.",
];

// O único 400 que não é da ligação: a nova palavra-passe é igual à atual.
const isSamePassword = (err: ApiError) => err.message.toLowerCase().includes("different from your current");

export default function ResetPasswordPage() {
  usePageMeta("Redefinir palavra-passe · ENEI 2027", "Define uma nova palavra-passe para a tua conta ENEI 2027.");

  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const { pending, errors, fail, submit, formRef, alertRef } = useAuthForm();

  const mismatch = confirm.length > 0 && password !== confirm;

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    const problem = newPasswordError(password);
    if (problem) {
      fail(formMessage(problem));
      return;
    }
    if (password !== confirm) {
      fail(formMessage("As palavras-passe não coincidem."));
      return;
    }

    void submit(async () => {
      try {
        await http("/auth/reset-password", {
          method: "POST",
          body: { token, new_password: password },
        });
        // Não inicia sessão: o utilizador tem de fazer login a seguir.
        setDone(true);
      } catch (err) {
        if (err instanceof ApiError && err.status === 400 && isSamePassword(err)) {
          fail({ fields: { new_password: ["A nova palavra-passe tem de ser diferente da atual."] }, message: null });
        } else if (err instanceof ApiError && err.status === 400) {
          // Ligação expirada, já usada ou inválida: a página própria pede uma nova.
          navigate("/conta/link-expirado", { replace: true });
        } else {
          fail(formErrorsFrom(err, "Demasiadas tentativas."));
        }
      }
    });
  };

  // Sem token não há ligação a usar.
  if (!token) return <Navigate to="/conta/link-expirado" replace />;

  return (
    <AuthLayout
      eyebrow="SEGURANÇA"
      title="Protege a tua conta."
      lead="Escolhe uma palavra-passe única e difícil de adivinhar."
      points={points}
    >
      {done ? (
        <>
          <AuthStateIcon>
            <path d="m5 12.5 4.5 4.5L19 7.5" />
          </AuthStateIcon>
          <AuthEyebrow text="CONCLUÍDO" />
          <h2>Palavra-passe atualizada.</h2>
          <p role="status" className="auth-intro">
            Terminámos as sessões abertas noutros dispositivos. Inicia sessão com a nova palavra-passe.
          </p>
          <div className="auth-actions">
            <Link className="btn btn--primary" to="/conta">
              Entrar na conta
            </Link>
          </div>
        </>
      ) : (
        <>
          <AuthStateIcon>
            <rect x="5" y="10" width="14" height="11" rx="1" />
            <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" />
          </AuthStateIcon>
          <AuthEyebrow text="NOVA_CHAVE" />
          <h2>Define uma nova palavra-passe.</h2>
          <p className="auth-intro">A nova palavra-passe substituirá a anterior em todos os dispositivos.</p>

          <form ref={formRef} className="auth-form" onSubmit={handleSubmit}>
            <AuthField
              label="Nova palavra-passe"
              name="new_password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Nova palavra-passe"
              autoComplete="new-password"
              maxLength={200}
              error={errors.fields.new_password}
              required
            />
            <AuthField
              label="Confirmar palavra-passe"
              name="confirm_password"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Repete a palavra-passe"
              autoComplete="new-password"
              maxLength={200}
              error={mismatch ? ["As palavras-passe não coincidem."] : undefined}
              required
            />

            <PasswordRules password={password} variant="conta" />

            <AuthAlert message={errors.message} alertRef={alertRef} />

            <button className="btn btn--primary" type="submit" disabled={pending} aria-busy={pending}>
              {pending ? "A guardar…" : "Guardar palavra-passe"}
            </button>
          </form>

          <p className="auth-switch">
            <Link className="auth-back" to="/conta">
              ← Voltar ao início de sessão
            </Link>
          </p>
        </>
      )}
    </AuthLayout>
  );
}
