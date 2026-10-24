import { useState, type SyntheticEvent } from "react";
import { Link } from "react-router-dom";
import AuthLayout, { AuthEyebrow, AuthStateIcon } from "../components/auth/AuthLayout";
import AuthField from "../components/auth/AuthField";
import AuthAlert from "../components/auth/AuthAlert";
import { usePageMeta } from "../utils/usePageMeta";
import { formErrorsFrom, useAuthForm } from "../utils/authForm";
import { http } from "../utils/http";

const points = [
  "Introduz o email da conta.",
  "Abre a ligação de recuperação.",
  "Define uma nova palavra-passe.",
];

export default function ForgotPasswordPage() {
  usePageMeta("Recuperar palavra-passe · ENEI 2027", "Recupera o acesso à tua conta ENEI 2027.");

  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { pending, errors, fail, submit, formRef, alertRef } = useAuthForm();

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    void submit(async () => {
      setSent(false);
      try {
        await http("/auth/forgot-password", {
          method: "POST",
          body: { email: email.trim() },
        });
        // 200 → resposta sempre igual, exista a conta ou não
        setSent(true);
      } catch (err) {
        fail(formErrorsFrom(err, "Demasiados pedidos."));
      }
    });
  };

  return (
    <AuthLayout
      eyebrow="RECUPERAÇÃO"
      title="Volta à tua conta."
      lead="Enviaremos as instruções de recuperação para o email associado ao teu perfil."
      points={points}
    >
      <AuthStateIcon>
        <rect x="3" y="5" width="18" height="14" rx="1" />
        <path d="m4 7 8 6 8-6" />
      </AuthStateIcon>
      <AuthEyebrow text="PALAVRA-PASSE" />
      <h2>Recuperar acesso.</h2>
      <p className="auth-intro">
        Indica o teu email. Se existir uma conta associada, receberás as instruções.
      </p>

      <form ref={formRef} className="auth-form" onSubmit={handleSubmit}>
        <AuthField
          label="Email"
          name="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="nome@exemplo.pt"
          autoComplete="email"
          error={errors.fields.email}
          required
        />

        <AuthAlert message={errors.message} alertRef={alertRef} />
        {sent && (
          <p role="status" className="auth-status">
            Se existir uma conta com este email, vais receber uma ligação de recuperação em breve. A
            ligação é válida durante 15 minutos e só pode ser usada uma vez.
          </p>
        )}

        <button className="btn btn--primary" type="submit" disabled={pending} aria-busy={pending}>
          {pending ? "A enviar…" : "Enviar ligação"}
        </button>
      </form>

      <p className="auth-switch">
        <Link className="auth-back" to="/conta">
          ← Voltar ao início de sessão
        </Link>
      </p>
    </AuthLayout>
  );
}
