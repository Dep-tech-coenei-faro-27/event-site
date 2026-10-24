import { useState, type SyntheticEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams, type Location } from "react-router-dom";
import AuthLayout, { AuthEyebrow } from "../components/auth/AuthLayout";
import AuthField from "../components/auth/AuthField";
import AuthAlert from "../components/auth/AuthAlert";
import { usePageMeta } from "../utils/usePageMeta";
import { formErrorsFrom, formMessage, useAuthForm } from "../utils/authForm";
import { http, ApiError } from "../utils/http";

const points = [
  "Consulta o estado dos teus bilhetes.",
  "Atualiza os dados do teu perfil.",
  "Recebe informação importante do evento.",
];

// Página para onde voltar depois de entrar: a que o ProtectedRoute guardou em `state.from`.
// Só caminhos internos (nunca «//outro-site»).
function redirectTarget(state: unknown): string {
  const from = (state as { from?: Location } | null)?.from;
  const path = from ? `${from.pathname}${from.search}${from.hash}` : "";
  return path.startsWith("/") && !path.startsWith("//") ? path : "/perfil";
}

export default function LoginPage() {
  usePageMeta("Entrar · ENEI 2027", "Entra na tua conta ENEI 2027 para acompanhares a tua inscrição.");

  const location = useLocation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // O AuthContext e o Perfil mandam para `/conta?sessao=terminada` quando a sessão acaba (401).
  const [sessionEnded, setSessionEnded] = useState(() => params.get("sessao") === "terminada");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const { pending, errors, fail, submit, formRef, alertRef } = useAuthForm();

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    void submit(async () => {
      setSessionEnded(false);
      try {
        await http("/auth/login", {
          method: "POST",
          body: { email, password, remember_me: rememberMe },
        });
        // 200 → cookie de sessão já guardado pelo browser
        window.location.href = redirectTarget(location.state);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          fail(formMessage("Email ou palavra-passe inválidos."));
        } else if (err instanceof ApiError && err.status === 403) {
          // Conta por verificar: a página própria explica e deixa reenviar o email.
          navigate("/conta/por-verificar", { state: { email } });
        } else {
          fail(formErrorsFrom(err, "Demasiadas tentativas de login."));
        }
      }
    });
  };

  return (
    <AuthLayout
      eyebrow="CONTA_ENEI"
      title="A tua experiência começa aqui."
      lead="Entra para acompanhar a tua inscrição e manter os teus dados do evento organizados."
      points={points}
    >
      <AuthEyebrow text="ENTRAR" />
      <h2>Bem-vindo de volta.</h2>
      <p className="auth-intro">Usa o email associado à tua conta ENEI.</p>

      {sessionEnded && (
        <p role="status" className="auth-status">
          A tua sessão terminou. Entra novamente.
        </p>
      )}

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
        <AuthField
          label="Palavra-passe"
          name="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="A tua palavra-passe"
          autoComplete="current-password"
          maxLength={200}
          error={errors.fields.password}
          required
        />

        <div className="auth-options">
          <label className="auth-check">
            <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />
            <span>Manter sessão iniciada</span>
          </label>
          <Link to="/conta/recuperar">Esqueceste-te da palavra-passe?</Link>
        </div>

        <AuthAlert message={errors.message} alertRef={alertRef} />

        <button className="btn btn--primary" type="submit" disabled={pending} aria-busy={pending}>
          {pending ? "A entrar…" : "Entrar na conta"}
        </button>
      </form>

      <div className="auth-divider">Ainda não tens conta?</div>
      <Link className="btn btn--secondary" to="/conta/criar">
        Criar conta
      </Link>
    </AuthLayout>
  );
}
