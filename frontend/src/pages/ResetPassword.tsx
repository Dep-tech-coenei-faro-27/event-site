import { useMemo, useState, type SyntheticEvent } from "react";
import Eyebrow from "../components/EyeBrow";
import PrimaryButton from "../components/PrimaryButton";
import SecondaryButton from "../components/SecundaryButton";
import Field from "../components/Field";

const points = [
  "Evita palavras-passe reutilizadas.",
  "Combina letras, números e símbolos.",
  "Guarda-a num gestor de palavras-passe.",
];

const rules = [
  { label: "Mínimo de 8 caracteres", test: (p: string) => p.length >= 8 },
  { label: "Uma letra maiúscula", test: (p: string) => /[A-Z]/.test(p) },
  { label: "Um número", test: (p: string) => /\d/.test(p) },
  { label: "Um símbolo", test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

// O backend responde em inglês; traduzimos as mensagens conhecidas do 400.
function messageFor400(detail: string): string {
  const d = detail.toLowerCase();
  if (d.includes("expired"))
    return "A ligação expirou. Pede uma nova ligação de recuperação.";
  if (d.includes("already been used"))
    return "Esta ligação já foi utilizada. Pede uma nova ligação de recuperação.";
  if (d.includes("different from your current"))
    return "A nova palavra-passe tem de ser diferente da atual.";
  return "Ligação inválida. Pede uma nova ligação de recuperação.";
}

export default function ResetPasswordPage() {
  const token = useMemo(
    () => new URLSearchParams(window.location.search).get("token") ?? "",
    [],
  );

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  // Quando o erro obriga a pedir nova ligação, mostramos o atalho.
  const [needsNewLink, setNeedsNewLink] = useState(!token);

  const allRulesMet = rules.every((r) => r.test(password));
  const mismatch = confirm.length > 0 && password !== confirm;

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;
    setError(null);

    if (!allRulesMet) {
      setError("A palavra-passe não cumpre todos os requisitos.");
      return;
    }
    if (password !== confirm) {
      setError("As palavras-passe não coincidem.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });

      if (res.ok) {
        // Não inicia sessão: o utilizador tem de fazer login a seguir.
        setDone(true);
        return;
      }

      if (res.status === 400) {
        const body = await res.json().catch(() => null);
        const detail = String(body?.message ?? body?.detail ?? "");
        setError(messageFor400(detail));
        if (!detail.toLowerCase().includes("different from your current")) {
          setNeedsNewLink(true);
        }
      } else if (res.status === 422) {
        setError("A palavra-passe não cumpre os requisitos de segurança.");
      } else if (res.status === 429) {
        setError("Demasiadas tentativas. Tenta novamente daqui a pouco.");
      } else {
        setError("Ocorreu um erro. Tenta novamente.");
      }
    } catch {
      setError("Não foi possível contactar o servidor.");
    } finally {
      setLoading(false);
    }
  };

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
                <Eyebrow text="SEGURANÇA" />
                <h1 className="max-w-[520px] text-[clamp(38px,5vw,64px)] leading-[1.06] tracking-[-0.045em]">
                  Protege a tua conta.
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
              <div
                aria-hidden="true"
                className="mb-6 grid size-16 place-items-center border border-[rgba(26,178,255,0.42)] bg-[rgba(26,178,255,0.08)] text-acento-forte"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="size-[31px] fill-none stroke-current stroke-[1.7]"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {done ? (
                    <path d="m5 12.5 4.5 4.5L19 7.5" />
                  ) : (
                    <>
                      <rect x="5" y="10" width="14" height="11" rx="1" />
                      <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" />
                    </>
                  )}
                </svg>
              </div>

              {done ? (
                <>
                  <Eyebrow text="CONCLUÍDO" />
                  <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                    Palavra-passe atualizada.
                  </h2>
                  <p
                    role="status"
                    className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto"
                  >
                    Terminámos as sessões abertas noutros dispositivos. Inicia
                    sessão com a nova palavra-passe.
                  </p>
                  <SecondaryButton
                    text="Entrar na conta"
                    to="/conta/"
                    className="w-full"
                  />
                </>
              ) : (
                <>
                  <Eyebrow text="NOVA_CHAVE" />
                  <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                    Define uma nova palavra-passe.
                  </h2>
                  <p className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto">
                    A nova palavra-passe substituirá a anterior em todos os
                    dispositivos.
                  </p>

                  <form className="grid gap-[18px]" onSubmit={handleSubmit}>
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
                      label="Confirmar palavra-passe"
                      name="confirm_password"
                      type="password"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      placeholder="Repete a palavra-passe"
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
                    {needsNewLink && (
                      <a
                        href="/conta/recuperar/"
                        className="text-[13px] font-semibold text-acento-forte"
                      >
                        Pedir nova ligação de recuperação
                      </a>
                    )}

                    <PrimaryButton
                      type="submit"
                      text={loading ? "A guardar..." : "Guardar palavra-passe"}
                      disabled={loading || !token}
                      className="w-full"
                    />
                  </form>

                  <p className="mt-6 text-center text-sm">
                    <a href="/conta/" className="font-semibold text-acento-forte">
                      ← Voltar ao início de sessão
                    </a>
                  </p>
                </>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}