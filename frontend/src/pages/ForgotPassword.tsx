import { useState, type SyntheticEvent } from "react";
import Eyebrow from "../components/EyeBrow";
import PrimaryButton from "../components/PrimaryButton";
import Field from "../components/Field";

const points = [
  "Introduz o email da conta.",
  "Abre a ligação de recuperação.",
  "Define uma nova palavra-passe.",
];

type Status = "idle" | "loading" | "sent" | "error";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (status === "loading") return;
    setError(null);
    setStatus("loading");

    try {
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });

      // 200 → resposta sempre igual, exista a conta ou não
      if (res.ok) {
        setStatus("sent");
        return;
      }

      if (res.status === 429) {
        setError("Demasiados pedidos. Tenta novamente daqui a pouco.");
      } else {
        setError("Ocorreu um erro. Tenta novamente.");
      }
    } catch {
      setError("Não foi possível contactar o servidor.");
    }
    setStatus("error");
  };

  const loading = status === "loading";

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
                <Eyebrow text="RECUPERAÇÃO" />
                <h1 className="max-w-[520px] text-[clamp(38px,5vw,64px)] leading-[1.06] tracking-[-0.045em]">
                  Volta à tua conta.
                </h1>
                <p className="mt-5 max-w-[720px] text-[17px] text-cinza-texto">
                  Enviaremos as instruções de recuperação para o email associado
                  ao teu perfil.
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
                  <rect x="3" y="5" width="18" height="14" rx="1" />
                  <path d="m4 7 8 6 8-6" />
                </svg>
              </div>

              <Eyebrow text="PALAVRA_PASSE" />
              <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                Recuperar acesso.
              </h2>
              <p className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto">
                Indica o teu email. Se existir uma conta associada, receberás as
                instruções.
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

                {error && (
                  <p role="alert" className="text-[13px] text-red-400">
                    {error}
                  </p>
                )}
                {status === "sent" && (
                  <p
                    role="status"
                    className="border-l-[3px] border-acento-principal bg-[rgba(26,178,255,0.07)] px-3.5 py-3 text-xs text-cinza-texto"
                  >
                    Se existir uma conta com este email, vais receber uma ligação
                    de recuperação em breve. A ligação é válida durante 15
                    minutos e só pode ser usada uma vez.
                  </p>
                )}

                <PrimaryButton
                  type="submit"
                  text={loading ? "A enviar..." : "Enviar ligação"}
                  disabled={loading}
                  className="w-full"
                />
              </form>

              <p className="mt-6 text-center text-sm">
                <a href="/conta/" className="font-semibold text-acento-forte">
                  ← Voltar ao início de sessão
                </a>
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}