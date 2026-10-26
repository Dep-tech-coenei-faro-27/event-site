import { useState, type SyntheticEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout, { AuthEyebrow } from "../components/auth/AuthLayout";
import AuthField from "../components/auth/AuthField";
import AuthAlert from "../components/auth/AuthAlert";
import PasswordRules from "../components/PasswordRules";
import { usePageMeta } from "../utils/usePageMeta";
import { formErrorsFrom, formMessage, useAuthForm } from "../utils/authForm";
import { newPasswordError } from "../utils/passwordChange";
import { http, ApiError } from "../utils/http";

const points = [
  "Regista os teus dados essenciais.",
  "Confirma o email da tua conta.",
  "Completa o perfil quando quiseres.",
];

export default function RegisterPage() {
  usePageMeta("Criar conta · ENEI 2027", "Cria a tua conta ENEI 2027 e prepara a tua participação.");

  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [accepted, setAccepted] = useState(false);
  const { pending, errors, fail, submit, formRef, alertRef } = useAuthForm();

  const validate = (): string | null => {
    const cleanName = name.trim();
    if (cleanName.length < 1 || cleanName.length > 255) {
      return "O nome deve ter entre 1 e 255 caracteres.";
    }
    if (!/\p{L}/u.test(cleanName)) {
      return "O nome tem de incluir pelo menos uma letra.";
    }
    if (/[<>]/.test(cleanName) || /[\p{Cc}\p{Cf}]/u.test(cleanName)) {
      return "O nome contém caracteres não permitidos.";
    }
    if (!/^[\x21-\x7E]+$/.test(email.trim())) {
      return "O email só pode conter caracteres ASCII.";
    }
    const passwordProblem = newPasswordError(password);
    if (passwordProblem) {
      return passwordProblem;
    }
    if (password !== confirm) {
      return "As palavras-passe não coincidem.";
    }
    if (!accepted) {
      return "Tens de aceitar os termos e condições e a política de privacidade.";
    }
    return null;
  };

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      fail(formMessage(validationError));
      return;
    }

    void submit(async () => {
      try {
        await http("/auth/register", {
          method: "POST",
          body: {
            name: name.trim(),
            email: email.trim(),
            password,
            accept_terms: accepted,
          },
        });
        navigate("/conta/verificar", { state: { email: email.trim().toLowerCase(), registered: true } });
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          fail({ fields: { email: ["Já existe uma conta com este email."] }, message: null });
        } else {
          fail(formErrorsFrom(err, "Demasiados registos."));
        }
      }
    });
  };

  return (
    <AuthLayout
      eyebrow="NOVO_PARTICIPANTE"
      title="Cria a tua conta ENEI."
      lead="Um único espaço para preparares a participação e acompanhares todas as etapas."
      points={points}
      wide
    >
      <AuthEyebrow text="CRIAR_CONTA" />
      <h2>Vamos começar.</h2>
      <p className="auth-intro">Preenche os dados abaixo para criares a tua conta.</p>

      <form ref={formRef} className="auth-form" onSubmit={handleSubmit}>
        <AuthField
          label="Nome completo"
          name="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="O teu nome completo"
          autoComplete="name"
          maxLength={255}
          error={errors.fields.name}
          required
        />
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

        <div className="auth-field-row">
          <AuthField
            label="Palavra-passe"
            name="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Cria uma palavra-passe"
            autoComplete="new-password"
            maxLength={200}
            error={errors.fields.password}
            required
          />
          <AuthField
            label="Confirmar palavra-passe"
            name="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Repete a palavra-passe"
            autoComplete="new-password"
            maxLength={200}
            required
          />
        </div>

        <PasswordRules password={password} variant="conta" />

        <label className="auth-check">
          <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} required />
          <span>
            Li e aceito os{" "}
            <Link className="auth-legal-link" to="/termos">
              termos e condições
            </Link>{" "}
            e a{" "}
            <Link className="auth-legal-link" to="/privacidade">
              política de privacidade
            </Link>
            .<small className="auth-legal-version">Documentos legais · versão 1.0 · 8 outubro 2026</small>
          </span>
        </label>

        <AuthAlert message={errors.message} alertRef={alertRef} />

        <button className="btn btn--primary" type="submit" disabled={pending} aria-busy={pending}>
          {pending ? "A criar conta…" : "Criar conta"}
        </button>
      </form>

      <p className="auth-switch">
        Já tens conta? <Link to="/conta">Entrar</Link>
      </p>
    </AuthLayout>
  );
}
