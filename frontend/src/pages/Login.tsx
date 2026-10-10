import { useState, type SyntheticEvent } from "react";
import Eyebrow from "../components/EyeBrow";
import PrimaryButton from "../components/PrimaryButton";
import SecondaryButton from "../components/SecundaryButton";
import Field from "../components/Field";
import { usePageMeta } from "../utils/usePageMeta";


const points = [
  "Consulta o estado dos teus bilhetes.",
  "Atualiza os dados do teu perfil.",
  "Recebe informação importante do evento.",
];


export default function LoginPage() {

    usePageMeta("Entrar · ENEI 2027", "Entra na tua conta ENEI 2027 para acompanhares a tua inscrição.");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // necessário para o cookie de sessão
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });

      if (res.ok) {
        // 200 → cookie de sessão já guardado pelo browser
        window.location.href = "/perfil"; // TODO: alterar para a url correta
        return;
      }

      if (res.status === 401) {
        setError("Email ou palavra-passe inválidos.");
      } else if (res.status === 403) {
        setError("Verifica o teu email antes de continuar.");
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
                <Eyebrow text="CONTA_ENEI" />
                <h1 className="max-w-[520px] text-[clamp(38px,5vw,64px)] leading-[1.06] tracking-[-0.045em]">
                  A tua experiência começa aqui.
                </h1>
                <p className="mt-5 max-w-[720px] text-[17px] text-cinza-texto">
                  Entra para acompanhar a tua inscrição e manter os teus dados
                  do evento organizados.
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
              <Eyebrow text="ENTRAR" />
              <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                Bem-vindo de volta.
              </h2>
              <p className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto">
                Usa o email associado à tua conta ENEI.
              </p>

              <form className="grid gap-[18px]" onSubmit={handleSubmit}>
                <Field
                  label="Email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nome@exemplo.pt"
                  autoComplete="email"
                  required
                />
                <Field
                  label="Palavra-passe"
                  name="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="A tua palavra-passe"
                  autoComplete="current-password"
                  maxLength={200}
                  required
                />

                <div className="flex items-start justify-between gap-2.5 text-[13px] max-[620px]:flex-col min-[621px]:items-center min-[621px]:gap-[18px]">
                  <label className="inline-flex cursor-pointer items-start gap-[9px] text-cinza-texto">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="mt-0.5 size-4 accent-acento-principal"
                    />
                    <span>Manter sessão iniciada</span>
                  </label>
                  <a
                    href="/conta/recuperar/"
                    className="font-semibold text-acento-forte"
                  >
                    Esqueceste-te da palavra-passe?
                  </a>
                </div>

                {error && (
                  <p role="alert" className="text-[13px] text-red-400">
                    {error}
                  </p>
                )}
                <PrimaryButton type="submit" text={loading ? "A entrar..." : "Entrar na conta"} disabled={loading} className="w-full"/>
              </form>

              <div className="my-[26px] grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-[11px] uppercase tracking-[0.12em] text-cinza-subtil before:h-px before:bg-[rgba(215,227,244,0.1)] before:content-[''] after:h-px after:bg-[rgba(215,227,244,0.1)] after:content-['']">
                Ainda não tens conta?
              </div>
                <SecondaryButton text="Criar conta" to="/conta/criar" className="w-full"/>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
