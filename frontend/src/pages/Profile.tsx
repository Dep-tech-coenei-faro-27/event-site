import { useEffect, useState } from "react";
import Eyebrow from "../components/EyeBrow";
import SecondaryButton from "../components/SecundaryButton";
import { usePageMeta } from "../utils/usePageMeta";


/**
 * Perfil — conversão de conta/perfil/index.html.
 *
 * Contrato usado:
 *  - GET  /api/auth/me        → { id, name, email, role, is_verified }
 *                               401 sem sessão · 403 email por verificar
 *  - POST /api/auth/logout
 *
 * Não existe endpoint para editar nome/email, por isso "Dados pessoais" é só leitura.
 *
 */

type Me = {
  id: number | string;
  name: string;
  email: string;
  role: "user" | "admin";
  is_verified: boolean;
};

const BORDER = "border-[rgba(215,227,244,0.1)]";
const BORDER_ACCENT = "border-[rgba(26,178,255,0.42)]";

function initialsOf(name: string, email: string): string {
  const source = name.trim() || email.split("@")[0] || "?";
  const parts = source.split(/\s+/).filter(Boolean);
  const letters =
    parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : source.slice(0, 2);
  return letters.toUpperCase();
}

function goToLogin() {
  window.location.href = "/conta/";
}

export default function ProfilePage() {
    
    usePageMeta("O meu perfil · ENEI 2027", "Consulta e atualiza os teus dados de participante no ENEI 2027.",);

  const [loadState, setLoadState] = useState<
    "loading" | "ready" | "unverified" | "error"
  >("loading");
  const [me, setMe] = useState<Me | null>(null);


  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (res.status === 401) {
          goToLogin();
          return;
        }
        if (res.status === 403) {
          if (!cancelled) setLoadState("unverified");
          return;
        }
        if (!res.ok) throw new Error("bad status");
        const data = (await res.json()) as Me;
        if (cancelled) return;
        setMe(data);
        setLoadState("ready");
      } catch {
        if (!cancelled) setLoadState("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const name = me?.name ?? "";
  const email = me?.email ?? "";
  const firstName = name.trim().split(/\s+/)[0] || "participante";

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      goToLogin();
    }
  };

  const navLink =
    "block border-b-[3px] border-transparent px-5 py-[13px] text-[13px] text-cinza-texto max-[900px]:min-w-max min-[901px]:border-b-0 min-[901px]:border-l-[3px]";
  const navLinkActive = "!border-acento-principal bg-[rgba(26,178,255,0.07)] text-white";
  const panel = `border ${BORDER} bg-azul-painel px-[18px] py-[22px] min-[621px]:p-7`;
  const panelTitle =
    "text-[clamp(30px,4vw,52px)] leading-[1.06] tracking-[-0.045em]";

  return (
    <div className="azulejo-bg min-h-screen bg-azul-base pt-16 font-poppins leading-[1.65] text-white min-[621px]:pt-[76px] max-[620px]:pb-[84px]">
      <main id="conteudo" className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="azulejo-bg pointer-events-none absolute inset-0 bg-acento-principal opacity-[0.025]"
        />

        {/* Hero */}
        <header
          className={`relative z-[1] border-b ${BORDER} bg-[radial-gradient(circle_at_78%_12%,rgba(26,178,255,0.2),transparent_36%)] pb-[clamp(36px,5vw,56px)] pt-[clamp(48px,7vw,92px)]`}
        >
          <div className="mx-auto w-[min(calc(100%-28px),1180px)] min-[621px]:w-[min(calc(100%-40px),1180px)]">
            <Eyebrow text="MINHA_CONTA" />
            <h1 className="text-[clamp(38px,6vw,68px)] leading-[1.06] tracking-[-0.045em]">
              Olá, {firstName}.
            </h1>
            <p className="mt-5 max-w-[720px] text-[clamp(17px,2vw,20px)] text-cinza-texto">
              Gere os teus dados e acompanha a preparação para o ENEI 2027.
            </p>
          </div>
        </header>

        <section className="relative z-[1] py-[clamp(40px,6vw,72px)]">
          <div className="mx-auto grid w-[min(calc(100%-28px),1180px)] gap-6 min-[621px]:w-[min(calc(100%-40px),1180px)] min-[901px]:grid-cols-[220px_minmax(0,1fr)]">
            {/* Sidebar */}
            <aside className={`h-fit border ${BORDER} bg-azul-painel`}>
              <div className={`border-b ${BORDER} p-[22px]`}>
                <div className="mb-[13px] grid size-12 place-items-center bg-acento-principal font-extrabold text-[#02101c]">
                  {initialsOf(name, email)}
                </div>
                <strong>{name.trim() || "Participante"}</strong>
                <p className="m-0 text-cinza-texto">Conta ENEI</p>
              </div>
              <nav
                aria-label="Área pessoal"
                className="flex overflow-x-auto min-[901px]:block min-[901px]:overflow-visible"
              >
                <a href="#visao-geral" aria-current="page" className={`${navLink} ${navLinkActive}`}>
                  Visão geral
                </a>
                <a href="#dados" className={navLink}>
                  Dados pessoais
                </a>
                <a href="#seguranca" className={navLink}>
                  Segurança
                </a>
                <button
                  type="button"
                  onClick={handleLogout}
                  className={`${navLink} w-full cursor-pointer bg-transparent text-left`}
                >
                  Sair
                </button>
              </nav>
            </aside>

            {/* Conteúdo */}
            <div id="visao-geral" className="grid gap-[18px]">
              {loadState === "loading" && (
                <p role="status" className="text-cinza-texto">
                  A carregar o teu perfil…
                </p>
              )}
              {loadState === "unverified" && (
                <p role="alert" className="text-[13px] text-red-400">
                  Verifica o teu email antes de continuar. Procura a mensagem de
                  verificação na tua caixa de entrada.
                </p>
              )}
              {loadState === "error" && (
                <p role="alert" className="text-[13px] text-red-400">
                  Não foi possível carregar o teu perfil. Atualiza a página e tenta
                  novamente.
                </p>
              )}

              {loadState === "ready" && me && (
                <>
                  {/* Dados pessoais (só leitura: a API não tem endpoint de edição) */}
                  <article id="dados" className={panel}>
                    <div className="mb-6">
                      <Eyebrow text="PERFIL" />
                      <h2 className={panelTitle}>Dados pessoais</h2>
                      <p className="mb-0 mt-2 text-[13px] text-cinza-texto">
                        Os dados definidos quando criaste a conta.
                      </p>
                    </div>
                    <dl className="m-0 grid gap-[18px] min-[621px]:grid-cols-2">
                      <div>
                        <dt className="font-montserrat text-xs font-semibold text-[#d7e3f4]">
                          Nome completo
                        </dt>
                        <dd className="m-0 mt-2 break-words">{me.name}</dd>
                      </div>
                      <div>
                        <dt className="font-montserrat text-xs font-semibold text-[#d7e3f4]">
                          Email
                        </dt>
                        <dd className="m-0 mt-2 break-all">{me.email}</dd>
                      </div>
                    </dl>
                  </article>

                  {/* Inscrição */}
                  <article className={panel}>
                    <div className="mb-6">
                      <Eyebrow text="PARTICIPAÇÃO" />
                      <h2 className={panelTitle}>Inscrição ENEI 2027</h2>
                      <p className="mb-0 mt-2 text-[13px] text-cinza-texto">
                        Estado e detalhes do bilhete.
                      </p>
                    </div>
                    <div
                      className={`border border-dashed ${BORDER_ACCENT} px-6 py-[42px] text-center`}
                    >
                      <h3 className="text-xl leading-[1.06] tracking-[-0.045em]">
                        Ainda não tens uma inscrição.
                      </h3>
                      <p className="mb-5 mt-3 text-cinza-texto">
                        Escolhe o teu bilhete para iniciares o processo de
                        participação.
                      </p>
                      <SecondaryButton text="Consultar bilhetes" to="/bilhetes/" />
                    </div>
                  </article>

                  {/* Segurança */}
                  <article id="seguranca" className={panel}>
                    <div className="flex flex-col gap-5 min-[621px]:flex-row min-[621px]:items-start min-[621px]:justify-between">
                      <div>
                        <Eyebrow text="SEGURANÇA" />
                        <h2 className={panelTitle}>Acesso à conta</h2>
                        <p className="mb-0 mt-2 text-[13px] text-cinza-texto">
                          Atualiza a palavra-passe e revê a segurança do perfil.
                        </p>
                      </div>
                      <SecondaryButton
                        text="Alterar palavra-passe"
                        to="/conta/alterar-palavra-passe"
                        className="max-[620px]:w-full"
                      />
                    </div>
                  </article>
                </>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}