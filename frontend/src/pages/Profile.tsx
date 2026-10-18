import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Eyebrow from "../components/EyeBrow";
import SecondaryButton from "../components/SecundaryButton";
import AccountLayout from "../components/dashboard/AccountLayout";
import AccountPanel from "../components/dashboard/AccountPanel";
import { BORDER, panelClass } from "../components/dashboard/AccountStyles";
import { useAuth } from "../utils/useAuth";
import { getMe } from "../utils/users";
import type { User } from "../utils/authContextValue";
import logo from "../assets/ENEI-logo.svg";
import TicketQr from "../components/TicketQr";

/** Visão geral: bilhete digital e preparação para o encontro. */
export default function ProfilePage() {
  const { user: authUser } = useAuth();
  const [profileUser, setProfileUser] = useState<User | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((data) => {
        if (!cancelled) setProfileUser(data);
      })
      .catch(() => {
        // Fallback silencioso para o utilizador do AuthContext se /users/me ainda não existir
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const me = profileUser ?? authUser;
  const firstName = (me?.name ?? "").trim().split(/\s+/)[0] || "Participante";

  // Lógica do QR de teste (Mock) — remover quando o backend entregar o qr_code
  const SAMPLE_QR =
    import.meta.env.VITE_QR_SAMPLE === "true"
      ? "ENEI27-EXEMPLO-0123456789abcdef0123456789abcdef"
      : null;

  const qrCode = me?.qr_code ?? SAMPLE_QR;

  // Estado de pagamento pendente (da API ou via variável de ambiente para teste)
  const isPaymentPending =
    !qrCode &&
    (me?.payment_status === "pending" ||
      me?.ticket_status === "pending" ||
      import.meta.env.VITE_TICKET_PENDING === "true");

  return (
    <AccountLayout
      metaTitle="Dashboard · ENEI 2027"
      metaDescription="Dashboard pessoal, bilhete digital e definições de perfil do ENEI 2027."
      eyebrow="ÁREA PESSOAL"
      title={`Olá, ${firstName}.`}
      lead="Consulta o bilhete digital e mantém os dados da tua conta atualizados."
    >
      {me && (
        <>
          {qrCode ? (
            /* ======== 1. ESTADO: COM BILHETE COMPRADO ======== */
            <article id="bilhete" className={`flex flex-col border ${BORDER} bg-azul-painel`}>
              <header
                className={`flex flex-wrap items-center justify-between gap-3 border-b ${BORDER} px-5 py-3.5 min-[621px]:px-6`}
              >
                <div className="flex items-center gap-3">
                  <img src={logo} alt="" className="h-7 w-auto object-contain opacity-90" />
                  <div className="flex flex-col">
                    <strong className="text-[14px] font-bold leading-tight text-white">
                      ENEI Faro 2027
                    </strong>
                    <span className="text-[12px] text-cinza-texto">Bilhete digital · 1–4 abril</span>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1.5 border border-[#10b981]/35 bg-[#10b981]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#10b981]">
                  <span className="size-1.5 rounded-full bg-[#10b981]" />
                  Confirmado
                </span>
              </header>

              <div className="grid min-[861px]:grid-cols-[minmax(0,1fr)_270px]">
                <section className="p-5 min-[621px]:p-6">
                  <Eyebrow text="A TUA MODALIDADE" />
                  <h2 className="mt-2 text-[clamp(28px,3.2vw,42px)] font-extrabold leading-[1.04] tracking-[-0.04em] text-white">
                    Experiência
                    <br />
                    completa
                  </h2>
                  <p className="mt-3 max-w-[380px] text-[14px] leading-relaxed text-cinza-texto min-[621px]:text-[15px]">
                    Entrada, refeições e alojamento para os quatro dias do encontro.
                  </p>

                  <dl className={`mt-6 grid grid-cols-2 gap-4 border-t ${BORDER} pt-5 min-[621px]:grid-cols-3`}>
                    <div>
                      <dt className="text-[11px] text-cinza-texto">Titular</dt>
                      <dd className="m-0 mt-0.5 truncate text-[13px] font-bold text-white">
                        {me.name || "Participante Exemplo"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[11px] text-cinza-texto">Datas</dt>
                      <dd className="m-0 mt-0.5 text-[13px] font-bold text-white">1–4 abril 2027</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] text-cinza-texto">Referência</dt>
                      <dd className="m-0 mt-0.5 text-[13px] font-bold text-white">ENEI—XXXX</dd>
                    </div>
                  </dl>

                  <div className="mt-6 flex flex-wrap items-center gap-3 print:hidden">
                    <Link
                      to="/informacao-ajuda/"
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-acento-principal px-5 py-2.5 text-[12px] font-bold uppercase tracking-wide text-[#02101c] transition-colors hover:bg-acento-principal/90"
                    >
                      <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M5 7h14v13H5zM9 11v5M15 11v5" />
                      </svg>
                      <span>Preparar viagem</span>
                    </Link>

                    <Link
                      to="/bilhetes/"
                      className={`inline-flex items-center justify-center gap-2 rounded-full border ${BORDER} bg-transparent px-5 py-2.5 text-[12px] font-bold text-white transition-colors hover:bg-white/5`}
                    >
                      <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                        <circle cx="12" cy="12" r="8" />
                        <path d="M12 11v5M12 8h.01" />
                      </svg>
                      <span>Ver modalidade</span>
                    </Link>
                  </div>
                </section>

                <section
                  aria-label="Código de entrada do bilhete"
                  className={`flex flex-col items-center justify-center border-t ${BORDER} bg-black/20 p-5 min-[621px]:p-6 min-[861px]:border-l min-[861px]:border-t-0`}
                >
                  <div className="text-center">
                    <p className="m-0 text-[10px] font-bold uppercase tracking-[0.14em] text-acento-principal">
                      Bilhete digital
                    </p>
                    <span className="mt-0.5 block text-[12px] text-cinza-texto">Apresenta à entrada</span>
                  </div>

                  <TicketQr code={qrCode} size={160} className="mt-4" />

                  <p className="mb-0 mt-3.5 max-w-[190px] text-center text-[11px] leading-snug text-cinza-texto">
                    Aumenta o brilho do ecrã para uma leitura rápida.
                  </p>
                </section>
              </div>

              <footer
                className={`flex flex-wrap items-center gap-x-6 gap-y-2 border-t ${BORDER} bg-white/[0.01] px-5 py-3 text-[12px] text-cinza-texto min-[621px]:px-6`}
              >
                <span className="inline-flex items-center gap-2">
                  <span className="text-[#10b981]">✓</span> Email verificado
                </span>
                <span className="inline-flex items-center gap-2">
                  <span className="text-[#10b981]">✓</span> Bilhete pessoal e intransmissível
                </span>
              </footer>
            </article>
          ) : isPaymentPending ? (
            /* ======== 2. ESTADO: PAGAMENTO PENDENTE ======== */
            <AccountPanel
              id="bilhete"
              eyebrow="PARTICIPAÇÃO"
              title="Inscrição ENEI 2027"
              description="Estado e detalhes do bilhete."
              action={
                <span className="inline-flex items-center gap-1.5 border border-areia/45 bg-areia/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-areia">
                  <span className="size-1.5 rounded-full bg-areia" />
                  Pagamento pendente
                </span>
              }
            >
              <div className="border border-dashed border-areia/45 bg-areia/[0.03] px-6 py-9 text-center">
                <h3 className="text-lg font-bold leading-[1.06] tracking-[-0.03em] text-white">
                  O teu pagamento está pendente de confirmação.
                </h3>
                <p className="mx-auto mb-5 mt-2.5 max-w-[520px] text-[14px] text-cinza-texto">
                  Assim que o pagamento for validado, o teu bilhete digital e o código QR ficarão disponíveis aqui automaticamente.
                </p>
                <SecondaryButton text="Precisas de ajuda?" to="/informacao-ajuda/" />
              </div>
            </AccountPanel>
          ) : (
            /* ======== 3. ESTADO: SEM BILHETE ======== */
            <AccountPanel
              id="bilhete"
              eyebrow="PARTICIPAÇÃO"
              title="Inscrição ENEI 2027"
              description="Estado e detalhes do bilhete."
            >
              <div className="border border-dashed border-[rgba(26,178,255,0.42)] px-6 py-9 text-center">
                <h3 className="text-lg font-bold leading-[1.06] tracking-[-0.03em]">
                  Ainda não tens uma inscrição.
                </h3>
                <p className="mb-5 mt-2.5 text-[14px] text-cinza-texto">
                  Escolhe o teu bilhete para iniciares o processo de participação.
                </p>
                <SecondaryButton text="Consultar bilhetes" to="/bilhetes/" />
              </div>
            </AccountPanel>
          )}

          {/* Antes do Encontro */}
          <section aria-labelledby="account-ready-title" className={`${panelClass} print:hidden`}>
            <header className="flex flex-col gap-4 min-[768px]:flex-row min-[768px]:items-center min-[768px]:justify-between min-[768px]:gap-8">
              <div className="min-w-0">
                <Eyebrow text="ANTES DO ENCONTRO" />
                <h2
                  id="account-ready-title"
                  className="mt-2 text-[clamp(26px,3vw,42px)] font-extrabold leading-[1.08] tracking-[-0.04em] text-white"
                >
                  Tudo num só lugar.
                </h2>
              </div>
              <p className="m-0 max-w-[380px] text-[14px] leading-relaxed text-cinza-texto min-[768px]:text-[16px]">
                Confirma os teus dados e consulta os locais antes de viajar.
              </p>
            </header>

            <hr className={`my-7 border-t ${BORDER}`} />

            <div className="grid gap-6 min-[768px]:grid-cols-[1.15fr_0.85fr] min-[768px]:gap-0">
              <dl className="m-0 flex flex-col min-[768px]:pr-10">
                <div className={`grid grid-cols-[110px_1fr] items-baseline gap-3 border-b ${BORDER} py-5`}>
                  <dt className="text-[12px] text-cinza-texto">Universidade</dt>
                  <dd className="m-0 text-[14px] font-bold text-white">Campus de Gambelas</dd>
                </div>
                <div className={`grid grid-cols-[110px_1fr] items-baseline gap-3 border-b ${BORDER} py-5`}>
                  <dt className="text-[12px] text-cinza-texto">Alojamento</dt>
                  <dd className="m-0 text-[14px] font-bold leading-snug text-white">
                    Escola Secundária Tomás Cabreira
                  </dd>
                </div>
              </dl>

              <div
                className={`flex flex-col justify-between min-[768px]:min-h-[180px] min-[768px]:border-l ${BORDER} min-[768px]:pl-10`}
              >
                <div>
                  <p className="m-0 text-[13px] font-bold text-white">Preparação</p>
                  <ul className="mt-4 flex list-none flex-col gap-4 p-0">
                    <li className="flex items-center gap-3 text-[13px] text-cinza-texto">
                      <span className="size-3 shrink-0 rounded-full bg-[#10b981]" />
                      Email verificado
                    </li>
                    <li className="flex items-center gap-3 text-[13px] text-cinza-texto">
                      <span
                        className={`size-3 shrink-0 rounded-full ${
                          qrCode
                            ? "bg-[#10b981]"
                            : isPaymentPending
                              ? "bg-areia"
                              : "border border-cinza-texto/60"
                        }`}
                      />
                      {isPaymentPending ? "Pagamento em validação" : "Bilhete confirmado"}
                    </li>
                    <li className="flex items-center gap-3 text-[13px] text-cinza-texto">
                      <span className="size-3 shrink-0 rounded-full border border-cinza-texto/60" />
                      Confirmar os dados pessoais
                    </li>
                  </ul>
                </div>

                <Link
                  to="/conta/dados"
                  className="mt-6 inline-flex items-center gap-1.5 text-[12px] font-bold text-acento-principal transition-opacity hover:opacity-80"
                >
                  Rever dados pessoais →
                </Link>
              </div>
            </div>
          </section>
        </>
      )}
    </AccountLayout>
  );
}