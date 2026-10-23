import { useState, type SyntheticEvent } from "react";
import { Link } from "react-router-dom";
import eneiLogo from "../assets/ENEI-logo.svg";
import Eyebrow from "../components/EyeBrow";
import PrimaryButton from "../components/PrimaryButton";
import SecondaryButton from "../components/SecundaryButton";
import Field from "../components/Field";
import { usePageMeta } from "../utils/usePageMeta";
import { http, ApiError } from "../utils/http";
import { retryAfterMessage } from "../utils/RetryAfter";
import { validationMessages } from "../utils/ValidationErrors";

/**
 * Alterar a palavra-passe com sessão iniciada (PUT /api/auth/password).
 * A API devolve um cookie de sessão novo e termina as sessões noutros dispositivos.
 */

const points = [
  "Confirma primeiro a palavra-passe atual.",
  "As outras sessões abertas são terminadas.",
  "Recebes um email a avisar da alteração.",
];

const rules = [
  { label: "Mínimo de 8 caracteres", test: (p: string) => p.length >= 8 },
  { label: "Uma letra maiúscula", test: (p: string) => /[A-Z]/.test(p) },
  { label: "Um número", test: (p: string) => /\d/.test(p) },
  { label: "Um símbolo", test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

// Mesmo limite do backend (bcrypt só usa os primeiros 72 bytes).
const byteLength = (s: string) => new TextEncoder().encode(s).length;

function messageFor(err: unknown): string {
  if (!(err instanceof ApiError)) return "Não foi possível contactar o servidor.";

  switch (err.status) {
    case 400:
      return err.message.toLowerCase().includes("different from your current")
        ? "A nova palavra-passe tem de ser diferente da atual."
        : "Não foi possível alterar a palavra-passe. Tenta novamente.";
    case 401:
      return err.message === "Current password is incorrect"
        ? "A palavra-passe atual está incorreta."
        : "A tua sessão terminou. Entra novamente.";
    case 403:
      return "Confirma o teu email antes de alterares a palavra-passe.";
    case 422: {
      const msgs = validationMessages(err.detail);
      return msgs.length
        ? msgs.join(" ")
        : "A palavra-passe não cumpre os requisitos de segurança.";
    }
    case 429:
      return retryAfterMessage(err.retryAfter, "Demasiadas alterações de palavra-passe.");
    default:
      return "Ocorreu um erro. Tenta novamente.";
  }
}

export default function ChangePasswordPage() {
  usePageMeta(
    "Alterar palavra-passe · ENEI 2027",
    "Altera a palavra-passe da tua conta ENEI 2027.",
  );

  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const allRulesMet = rules.every((r) => r.test(password));
  const mismatch = confirm.length > 0 && password !== confirm;

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;
    setError(null);

    if (!allRulesMet) {
      setError("A nova palavra-passe não cumpre todos os requisitos.");
      return;
    }
    if (byteLength(password) > 72) {
      setError("A palavra-passe é demasiado longa.");
      return;
    }
    if (password !== confirm) {
      setError("As palavras-passe não coincidem.");
      return;
    }
    if (password === current) {
      setError("A nova palavra-passe tem de ser diferente da atual.");
      return;
    }

    setLoading(true);
    try {
      await http("/auth/password", {
        method: "PUT",
        body: { current_password: current, new_password: password },
      });
      setDone(true);
      setCurrent("");
      setPassword("");
      setConfirm("");
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="azulejo-bg min-h-screen bg-azul-base pt-16 font-poppins leading-[1.65] text-white min-[621px]:pt-[76px] max-[620px]:pb-[84px]">
      <div
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
                src={eneiLogo}
                alt=""
                aria-hidden="true"
                className="pointer-events-none absolute bottom-7 right-[34px] h-[206px] w-[86px] object-contain opacity-[0.07]"
              />
              <div className="relative">
                <Eyebrow text="SEGURANÇA" />
                <h1 className="max-w-[520px] text-[clamp(38px,5vw,64px)] leading-[1.06] tracking-[-0.045em]">
                  Atualiza o teu acesso.
                </h1>
                <p className="mt-5 max-w-[720px] text-[17px] text-cinza-texto">
                  Escolhe uma palavra-passe única e difícil de adivinhar.
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
            <div className="flex flex-col justify-center bg-[linear-gradient(145deg,rgba(26,178,255,0.035),transparent_45%)] bg-azul-painel px-[22px] py-[30px] min-[621px]:p-[clamp(38px,6vw,74px)]">
              {done ? (
                <>
                  <Eyebrow text="CONCLUÍDO" />
                  <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                    Palavra-passe alterada.
                  </h2>
                  <p
                    role="status"
                    className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto"
                  >
                    A tua sessão continua ativa neste dispositivo. Terminámos as
                    sessões abertas noutros dispositivos.
                  </p>
                  <SecondaryButton text="Voltar ao perfil" to="/perfil" className="w-full" />
                </>
              ) : (
                <>
                  <Eyebrow text="ALTERAR_PALAVRA-PASSE" />
                  <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                    Altera a tua palavra-passe.
                  </h2>
                  <p className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto">
                    Indica a palavra-passe atual e escolhe uma nova.
                  </p>

                  <form className="grid gap-[18px]" onSubmit={handleSubmit}>
                    <Field
                      label="Palavra-passe atual"
                      name="current_password"
                      type="password"
                      value={current}
                      onChange={(e) => setCurrent(e.target.value)}
                      placeholder="A tua palavra-passe atual"
                      autoComplete="current-password"
                      maxLength={200}
                      required
                    />
                    <Field
                      label="Nova palavra-passe"
                      name="new_password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Nova palavra-passe"
                      autoComplete="new-password"
                      maxLength={200}
                      required
                    />
                    <Field
                      label="Confirmar nova palavra-passe"
                      name="confirm_password"
                      type="password"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      placeholder="Repete a nova palavra-passe"
                      autoComplete="new-password"
                      maxLength={200}
                      required
                    />

                    <ul className="-mt-1 m-0 grid list-none grid-cols-1 gap-x-3.5 gap-y-1.5 p-0 text-[11px] min-[621px]:grid-cols-2">
                      {rules.map((r) => {
                        const ok = r.test(password);
                        return (
                          <li
                            key={r.label}
                            className={ok ? "text-acento-forte" : "text-cinza-subtil"}
                          >
                            <span className="mr-[7px] text-acento-principal">
                              {ok ? "✓" : "—"}
                            </span>
                            {r.label}
                          </li>
                        );
                      })}
                    </ul>

                    {mismatch && (
                      <p className="text-[13px] text-red-400">
                        As palavras-passe não coincidem.
                      </p>
                    )}
                    {error && (
                      <p role="alert" className="text-[13px] text-red-400">
                        {error}
                      </p>
                    )}

                    <PrimaryButton
                      type="submit"
                      text={loading ? "A guardar..." : "Guardar nova palavra-passe"}
                      disabled={loading}
                      className="w-full"
                    />
                  </form>

                  <p className="mt-6 text-center text-sm">
                    <Link to="/conta/recuperar" className="font-semibold text-acento-forte">
                      Não te lembras da palavra-passe atual?
                    </Link>
                  </p>
                  <p className="mt-2 text-center text-sm">
                    <Link to="/perfil" className="font-semibold text-acento-forte">
                      ← Voltar ao perfil
                    </Link>
                  </p>
                </>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
