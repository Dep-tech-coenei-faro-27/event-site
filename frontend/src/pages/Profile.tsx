import { useContext, useEffect } from "react";
import { Link } from "react-router-dom";
import Eyebrow from "../components/EyeBrow";
import SecondaryButton from "../components/SecundaryButton";
import AccountLayout from "../components/dashboard/AccountLayout";
import AccountPanel from "../components/dashboard/AccountPanel";
import StudentProofSection from "../components/dashboard/StudentProofSection";
import { BORDER, panelClass } from "../components/dashboard/AccountStyles";
import { useAuth } from "../utils/useAuth";
import { MeContext, useMeData } from "../utils/useMeData";
import logo from "../assets/ENEI-logo.svg";
import TicketQr from "../components/TicketQr";
import { EVENT_DATES } from "../data/Event";
import PageStatus from "../components/PageStatus";
import { loadErrorMessage } from "../utils/loadError";

/** Visão geral: bilhete digital e preparação para o encontro. */
export default function ProfilePage() {
  const { user: authUser } = useAuth();
  // Dentro da moldura da área pessoal os dados vêm dela (já carregados ao mudar de separador); fora, a página pede-os.
  const shared = useContext(MeContext);
  const own = useMeData(!shared);
  const { me, error: loadError, retry, revalidate } = shared ?? own;
  // Ao voltar a este separador atualiza-se em segundo plano, sem «a carregar» nem saltos.
  const isShared = shared !== null;
  useEffect(() => {
    if (isShared) revalidate();
  }, [isShared, revalidate]);

  // O nome da conta (atualizado logo ao guardar os dados pessoais) manda: `me` pode estar uma visita atrasado.
  const firstName = (authUser?.name ?? me?.name ?? "").trim().split(/\s+/)[0] || "Participante";

  const qrCode = me?.qr_code ?? null;
  const ticket = me?.ticket ?? null;
  // Estados da compra que a API devolve em /users/me: pagamento à espera ou reembolso a caminho.
  const pending = !qrCode ? (me?.pending_payment ?? null) : null;
  const refundDue = !qrCode && !pending ? (me?.refund_due ?? null) : null;

  return (
    <AccountLayout
      metaTitle="Área pessoal · ENEI 2027"
      metaDescription="Área pessoal, bilhete digital e definições de perfil do ENEI 2027."
      eyebrow="ÁREA PESSOAL"
      title={`Olá, ${firstName}.`}
      lead="Consulta o bilhete digital e mantém os dados da tua conta atualizados."
    >
      {!me && loadError === null && <PageStatus state="loading" />}
      {!me && loadError !== null && (
        <PageStatus
          state="error"
          title="Não foi possível carregar o teu bilhete."
          message={loadErrorMessage(loadError)}
          onRetry={retry}
        />
      )}
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
                    <span className="text-[12px] text-cinza-texto">Bilhete digital · {EVENT_DATES}</span>
                  </div>
                </div>
                <span className="inline-flex items-center gap-1.5 border border-[#10b981]/35 bg-[#10b981]/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#10b981]">
                  <span className="size-1.5 rounded-full bg-[#10b981]" />
                  Confirmado
                </span>
              </header>

              <div className="grid min-[861px]:grid-cols-[minmax(0,1fr)_300px]">
                <section className="p-5 min-[621px]:p-6">
                  <Eyebrow text="A TUA MODALIDADE" />
                  <h2 className="mt-2 text-[clamp(28px,3.2vw,42px)] font-extrabold leading-[1.04] tracking-[-0.04em] text-white">
                    {ticket?.tier_name ?? "Bilhete"}
                  </h2>

                  <dl className={`mt-6 grid grid-cols-2 gap-4 border-t ${BORDER} pt-5 min-[621px]:grid-cols-3`}>
                    <div>
                      <dt className="text-[11px] text-cinza-texto">Titular</dt>
                      <dd className="m-0 mt-0.5 truncate text-[13px] font-bold text-white">
                        {ticket?.holder_name ?? me.name}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[11px] text-cinza-texto">Datas</dt>
                      <dd className="m-0 mt-0.5 text-[13px] font-bold text-white">{EVENT_DATES}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] text-cinza-texto">Referência</dt>
                      <dd className="m-0 mt-0.5 text-[13px] font-bold text-white">{ticket?.reference ?? "—"}</dd>
                    </div>
                  </dl>

                  <div className="mt-6 flex flex-wrap items-center gap-3 print:hidden">
                    <Link
                      to="/informacao-ajuda#localizacoes"
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-acento-principal px-5 py-2.5 text-[12px] font-bold uppercase tracking-wide text-[#02101c] transition-colors hover:bg-acento-principal/90"
                    >
                      <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
                        <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M5 7h14v13H5zM9 11v5M15 11v5" />
                      </svg>
                      <span>Preparar viagem</span>
                    </Link>

                    <Link
                      to="/bilhetes#tipos"
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

                  <TicketQr code={qrCode} size={200} className="mt-4" />

                  <p className="mb-0 mt-3.5 max-w-[190px] text-center text-[11px] leading-snug text-cinza-texto">
                    Aumenta o brilho do ecrã para uma leitura rápida.
                  </p>
                </section>
              </div>

              <footer
                className={`flex flex-wrap items-center gap-x-6 gap-y-2 border-t ${BORDER} bg-white/[0.01] px-5 py-3 text-[12px] text-cinza-texto min-[621px]:px-6`}
              >
                {me.is_verified && (
                  <span className="inline-flex items-center gap-2">
                    <span className="text-[#10b981]">✓</span> Email verificado
                  </span>
                )}
                <span className="inline-flex items-center gap-2">
                  <span className="text-[#10b981]">✓</span> Bilhete pessoal e intransmissível
                </span>
              </footer>
            </article>
          ) : pending ? (
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
                  {pending.tier_name} · Referência {pending.reference}. Quando o pagamento for confirmado, o bilhete e o código QR aparecem aqui.
                </p>
                <SecondaryButton text="Precisas de ajuda?" to="/informacao-ajuda/" />
              </div>
            </AccountPanel>
          ) : refundDue ? (
            /* ======== 2b. ESTADO: REEMBOLSO A CAMINHO ======== */
            <AccountPanel
              id="bilhete"
              eyebrow="PARTICIPAÇÃO"
              title="Inscrição ENEI 2027"
              description="Estado e detalhes do bilhete."
            >
              <div className="border border-dashed border-areia/45 bg-areia/[0.03] px-6 py-9 text-center">
                <h3 className="text-lg font-bold leading-[1.06] tracking-[-0.03em] text-white">
                  O teu pagamento vai ser reembolsado.
                </h3>
                <p className="mx-auto mb-5 mt-2.5 max-w-[520px] text-[14px] text-cinza-texto">
                  Recebemos o pagamento {refundDue.reference} mas não foi possível emitir o bilhete. O valor vai ser devolvido.
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
                  Escolhe um bilhete para participares no ENEI.
                </p>
                <SecondaryButton text="Consultar bilhetes" to="/bilhetes/" />
              </div>
            </AccountPanel>
          )}

          <StudentProofSection
            status={me.student_verification_status}
            onStatusChange={revalidate}
            onStale={retry}
          />

          {/* Antes do Encontro */}
          <section aria-labelledby="account-ready-title" className={`${panelClass} print:hidden`}>
            <header className="flex flex-col gap-4 min-[768px]:flex-row min-[768px]:items-center min-[768px]:justify-between min-[768px]:gap-8">
              <div className="min-w-0">
                <Eyebrow text="ANTES DO ENCONTRO" />
                <h2
                  id="account-ready-title"
                  className="mt-2 text-[clamp(26px,3vw,42px)] font-extrabold leading-[1.08] tracking-[-0.04em] text-white"
                >
                  Antes de vires.
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
                      <span
                        className={`size-3 shrink-0 rounded-full ${me.is_verified ? "bg-[#10b981]" : "border border-cinza-texto/60"}`}
                      />
                      {me.is_verified ? "Email verificado" : "Email por verificar"}
                    </li>
                    <li className="flex items-center gap-3 text-[13px] text-cinza-texto">
                      <span
                        className={`size-3 shrink-0 rounded-full ${
                          qrCode
                            ? "bg-[#10b981]"
                            : pending
                              ? "bg-areia"
                              : "border border-cinza-texto/60"
                        }`}
                      />
                      {pending ? "Pagamento em validação" : "Bilhete confirmado"}
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
