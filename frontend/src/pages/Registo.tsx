import { useMemo, useState, type SyntheticEvent } from "react";
import Eyebrow from "../components/EyeBrow";
import PrimaryButton from "../components/PrimaryButton";
import Field from "../components/Field";
import { usePageMeta } from "../utils/usePageMeta";

import { validationMessages } from "../utils/ValidationErrors.ts";
import { retryAfterMessage } from "../utils/RetryAfter.ts";

const points = [
  "Regista os teus dados essenciais.",
  "Confirma o email da tua conta.",
  "Completa o perfil quando quiseres.",
];


function Rule({ ok, text }: { ok: boolean; text: string }) {
  return (
    <li
      className={`flex items-center gap-2 text-[11px] transition-colors ${
        ok ? "text-acento-forte" : "text-cinza-subtil"
      }`}
    >
      <span aria-hidden="true" className="text-acento-principal">
        {ok ? "✓" : "—"}
      </span>
      {text}
    </li>
  );
}

// Regras da API: símbolo = qualquer caracter fora de A-Z, a-z, 0-9
const hasUpper = (v: string) => /[A-Z]/.test(v);
const hasDigit = (v: string) => /[0-9]/.test(v);
const hasSymbol = (v: string) => /[^A-Za-z0-9]/.test(v);
const byteLength = (v: string) => new TextEncoder().encode(v).length;

export default function RegisterPage() {

    usePageMeta("Criar conta · ENEI 2027", "Cria a tua conta ENEI 2027 e prepara a tua participação.");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);

  const rules = useMemo(
    () => ({
      length: password.length >= 8 && password.length <= 200,
      upper: hasUpper(password),
      digit: hasDigit(password),
      symbol: hasSymbol(password),
    }),
    [password],
  );

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
    if (!rules.length || !rules.upper || !rules.digit || !rules.symbol) {
      return "A palavra-passe não cumpre todos os requisitos.";
    }
    if (byteLength(password) > 72) {
      return "A palavra-passe é demasiado longa (máximo de 72 bytes).";
    }
    if (password !== confirm) {
      return "As palavras-passe não coincidem.";
    }
    if (!accepted) {
      return "Tens de aceitar os termos e condições e a política de privacidade.";
    }
    return null;
  };

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (loading) return;

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          password,
        }),
      });

      if (res.status === 201) {
        setRegisteredEmail(email.trim().toLowerCase());
        return;
      }

      if (res.status === 409) {
        setError("Já existe uma conta com este email.");
      } else if (res.status === 422) {

            const body = await res.json().catch(() => null);
            const msgs = validationMessages(body?.detail);
            setError(msgs.length ? msgs.join(" ") : "Os dados enviados são inválidos. Verifica os campos.",);

      } else if (res.status === 429) {
            setError(retryAfterMessage(res, "Demasiados registos."));
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
                <Eyebrow text="NOVO_PARTICIPANTE" />
                <h1 className="max-w-[520px] text-[clamp(38px,5vw,64px)] leading-[1.06] tracking-[-0.045em]">
                  Cria a tua conta ENEI.
                </h1>
                <p className="mt-5 max-w-[720px] text-[17px] text-cinza-texto">
                  Um único espaço para preparares a participação e acompanhares todas as etapas.
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
              {registeredEmail ? (
                <div role="status">
                  <Eyebrow text="CONTA_CRIADA" />
                  <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                    Verifica o teu email.
                  </h2>
                  <p className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto">
                    Enviámos um email de verificação para{" "}
                    <strong className="text-white">{registeredEmail}</strong>. Confirma a tua
                    conta para poderes entrar.
                  </p>
                  <a href="/conta" className="font-semibold text-acento-forte">
                    Ir para o login
                  </a>
                </div>
              ) : (
                <>
                  <Eyebrow text="CRIAR_CONTA" />
                  <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
                    Vamos começar.
                  </h2>
                  <p className="mb-[30px] mt-3.5 max-w-[560px] text-cinza-texto">
                    Preenche os dados abaixo para visualizar o processo de registo.
                  </p>

                  <form className="grid gap-[18px]" onSubmit={handleSubmit}>
                    <Field
                      label="Nome completo"
                      name="name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="O teu nome completo"
                      autoComplete="name"
                      maxLength={255}
                      required
                    />
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

                    <div className="grid gap-[18px] min-[621px]:grid-cols-2">
                      <Field
                        label="Palavra-passe"
                        name="password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Cria uma palavra-passe"
                        autoComplete="new-password"
                        maxLength={200}
                        required
                      />
                      <Field
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

                    <ul className="-mt-2 grid list-none gap-x-[18px] gap-y-1.5 p-0 min-[621px]:grid-flow-col min-[621px]:grid-cols-2 min-[621px]:grid-rows-2">
                      <Rule ok={rules.length} text="Mínimo de 8 caracteres" />
                      <Rule ok={rules.digit} text="Um número" />
                      <Rule ok={rules.upper} text="Uma letra maiúscula" />
                      <Rule ok={rules.symbol} text="Um símbolo" />
                    </ul>

                    <label className="inline-flex cursor-pointer items-start gap-[9px] text-[15px] text-cinza-texto">
                      <input
                        type="checkbox"
                        checked={accepted}
                        onChange={(e) => setAccepted(e.target.checked)}
                        className="mt-1 size-4 accent-acento-principal"
                      />
                      <span>
                        Li e aceito os{" "}
                        <a href="/termos/" className="text-acento-forte underline">
                          termos e condições
                        </a>{" "}
                        e a{" "}
                        <a href="/privacidade/" className="text-acento-forte underline">
                          política de privacidade
                        </a>
                        .
                      </span>
                    </label>

                    {error && (
                      <p role="alert" className="text-[13px] text-red-400">
                        {error}
                      </p>
                    )}
                    
                    <PrimaryButton type="submit" text={loading ? "A criar conta..." : "Criar conta"} disabled={loading} className="w-full"/>
                  </form>

                  <p className="mt-[18px] text-center text-sm text-cinza-texto">
                    Já tens conta?{" "}
                    <a href="/conta/" className="font-semibold text-acento-forte">
                      Entrar
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