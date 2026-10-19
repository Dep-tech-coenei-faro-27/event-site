import { useCallback, useEffect, useState, type SyntheticEvent } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import eneiLogo from "../assets/ENEI-logo.svg";
import mbwayLogo from "../assets/mbway-logo.svg";
import Eyebrow from "../components/EyeBrow";
import PrimaryButton from "../components/PrimaryButton";
import SecondaryButton from "../components/SecundaryButton";
import { EVENT_DATES } from "../data/Event";
import { FEATURED_TICKET, TICKET_DESCRIPTIONS } from "../data/Tickets";
import { checkoutErrorFor, type CheckoutError } from "../utils/checkoutErrors";
import { formatCents } from "../utils/money";
import {
  fetchTicketTiers,
  initiatePayment,
  rememberPaymentReference,
  type TicketTier,
  type Transaction,
} from "../utils/payments";
import { normalizePtMobile, ptMobileError } from "../utils/phone";
import { cleanNif, nifError } from "../utils/nif";
import { usePageMeta } from "../utils/usePageMeta";
import { useAuth } from "../utils/useAuth";

/**
 * Checkout MB Way: /bilhetes/checkout?bilhete=<modalidade>.
 *
 * - Modalidades e preços vêm de GET /api/payment/tiers (nada escrito à mão).
 * - Um bilhete por pessoa: não há campo de quantidade.
 * - POST /api/payment/initiate com a modalidade e o telemóvel; o preço é do servidor.
 * - Depois do 201 mostra a referência e pede para confirmar no MB Way. O polling do
 *   estado do pagamento é a issue #154.
 */

type TiersState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; tiers: TicketTier[] };

const BORDER = "border-[rgba(215,227,244,0.1)]";
const BORDER_ACCENT = "border-[rgba(26,178,255,0.42)]";
const panelClass = `border ${BORDER_ACCENT} bg-azul-painel`;
const linkClass = "font-semibold text-acento-forte hover:text-white";

function priceLabel(tier: TicketTier): string {
  if (!tier.sale_open || tier.price_cents === null) return "A confirmar";
  if (!tier.available) return "Esgotado";
  return formatCents(tier.price_cents, tier.currency);
}

// Modalidade a mostrar escolhida: a do URL, se se puder comprar, senão a primeira disponível.
function initialChoice(tiers: TicketTier[], wanted: string | null): string | null {
  const available = tiers.filter((t) => t.available);
  return (available.find((t) => t.tier === wanted) ?? available[0])?.tier ?? null;
}

function useCooldown() {
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (until <= now) return;
    const id = window.setTimeout(() => setNow(Date.now()), 1000);
    return () => window.clearTimeout(id);
  }, [until, now]);

  const start = useCallback((seconds: number) => {
    const t = Date.now();
    setNow(t);
    setUntil(t + seconds * 1000);
  }, []);

  return { active: until > now, secondsLeft: Math.ceil((until - now) / 1000), start };
}

/* ------------------------------------------------------------------ */

function CheckoutHeading({ step }: { step: 2 | 3 }) {
  const steps = ["Bilhete", "Pagamento", "Confirmação"];
  return (
    <header
      className={`relative overflow-hidden border-b ${BORDER_ACCENT} bg-azul-superficie bg-[radial-gradient(circle_at_82%_22%,rgba(26,178,255,0.15),transparent_30%)] pb-[42px] pt-[clamp(46px,7vw,88px)]`}
    >
      <div className="relative z-[1] mx-auto w-[min(calc(100%-28px),1180px)] min-[621px]:w-[min(calc(100%-40px),1180px)]">
        <Link
          to="/bilhetes#tipos"
          className="mb-9 inline-flex text-[13px] font-semibold text-cinza-texto hover:text-acento-forte"
        >
          ← Voltar aos bilhetes
        </Link>
        <div className="grid items-end gap-[18px] min-[701px]:grid-cols-[minmax(0,1.25fr)_minmax(280px,0.75fr)] min-[701px]:gap-12">
          <div>
            <Eyebrow text="CHECKOUT" />
            <h1 className="max-w-[720px] text-[clamp(38px,6vw,76px)] leading-[1.06] tracking-[-0.045em]">
              Finaliza a tua inscrição.
            </h1>
          </div>
          <p className="mb-2 text-[clamp(17px,2vw,20px)] text-cinza-texto">
            Escolhe o bilhete e conclui o pagamento através de MB Way.
          </p>
        </div>
        <ol
          aria-label="Etapas da compra"
          className={`m-0 mt-[34px] grid list-none grid-cols-3 border-t ${BORDER} p-0 min-[701px]:mt-12`}
        >
          {steps.map((label, i) => {
            const active = i < step;
            return (
              <li
                key={label}
                aria-current={i === step - 1 ? "step" : undefined}
                className={`relative grid gap-1 pr-2 pt-[18px] text-xs min-[701px]:flex min-[701px]:gap-3 min-[701px]:pr-5 ${
                  active ? "text-white" : "text-cinza-subtil"
                }`}
              >
                <span
                  aria-hidden="true"
                  className={`absolute -top-[2px] left-0 h-[3px] bg-acento-principal ${active ? "w-full" : "w-0"}`}
                />
                <span className="font-montserrat font-bold text-acento-forte">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <strong>{label}</strong>
              </li>
            );
          })}
        </ol>
      </div>
    </header>
  );
}

function PanelHeading({ n, eyebrow, id, title, text }: {
  n: string;
  eyebrow: string;
  id: string;
  title: string;
  text: string;
}) {
  return (
    <div
      className={`grid grid-cols-[40px_minmax(0,1fr)] items-start gap-3.5 border-b ${BORDER} pb-[30px] min-[701px]:grid-cols-[48px_minmax(0,1fr)] min-[701px]:gap-5`}
    >
      <span
        aria-hidden="true"
        className={`grid size-10 place-items-center border ${BORDER_ACCENT} font-montserrat text-xs font-bold text-acento-forte min-[701px]:size-12`}
      >
        {n}
      </span>
      <div>
        <Eyebrow text={eyebrow} />
        <h2 id={id} className="text-[clamp(28px,3.4vw,42px)] leading-[1.06] tracking-[-0.045em]">
          {title}
        </h2>
        <p className="mb-0 mt-2.5 text-cinza-texto">{text}</p>
      </div>
    </div>
  );
}

function TierOption({ tier, checked, onChange }: {
  tier: TicketTier;
  checked: boolean;
  onChange: (tier: string) => void;
}) {
  const featured = tier.tier === FEATURED_TICKET;
  const disabled = !tier.available;
  const category = `${featured ? "RECOMENDADO · " : ""}${tier.is_student ? "ESTUDANTE" : "NÃO ESTUDANTE"}`;
  const description = TICKET_DESCRIPTIONS[tier.tier];

  const selected = featured
    ? "border-areia bg-[linear-gradient(90deg,rgba(229,191,120,0.08),transparent_55%)] shadow-[inset_4px_0_0_#E5BF78]"
    : "border-acento-principal bg-[rgba(26,178,255,0.065)] shadow-[inset_4px_0_0_#1AB2FF]";

  return (
    <label
      className={`relative grid min-h-[96px] grid-cols-[22px_minmax(0,1fr)] items-center gap-4 border px-3.5 py-4 transition-[border-color,background-color,transform] duration-200 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-acento-forte min-[701px]:grid-cols-[24px_minmax(0,1fr)_auto] min-[701px]:px-5 min-[701px]:py-[18px] ${
        checked ? selected : `${BORDER} bg-azul-base`
      } ${disabled ? "cursor-not-allowed opacity-55" : "cursor-pointer hover:-translate-y-0.5 hover:border-[rgba(26,178,255,0.42)]"}`}
    >
      <input
        type="radio"
        name="ticket"
        value={tier.tier}
        checked={checked}
        disabled={disabled}
        onChange={() => onChange(tier.tier)}
        className="absolute opacity-0"
      />
      <span
        aria-hidden="true"
        className={`grid size-5 place-items-center rounded-full border-2 ${checked ? "border-acento-principal" : "border-cinza-subtil"}`}
      >
        <span
          className={`size-2 rounded-full bg-acento-principal transition-transform duration-200 ${checked ? "scale-100" : "scale-0"}`}
        />
      </span>
      <span className="grid min-w-0 gap-[3px]">
        <small className="font-montserrat text-[9px] font-bold tracking-[0.12em] text-acento-forte">
          {category}
        </small>
        <strong className="text-[17px]">{tier.name}</strong>
        {description && <span className="text-xs text-cinza-texto">{description}</span>}
      </span>
      <span className="col-start-2 whitespace-nowrap text-xs font-bold text-white min-[701px]:col-start-auto">
        {priceLabel(tier)}
      </span>
    </label>
  );
}

function Summary({ tier }: { tier: TicketTier | null }) {
  const price =
    tier && tier.price_cents !== null ? formatCents(tier.price_cents, tier.currency) : "A confirmar";

  return (
    <aside
      aria-labelledby="summary-heading"
      className={`${panelClass} px-5 py-6 min-[981px]:sticky min-[981px]:top-[100px] min-[981px]:p-[30px]`}
    >
      <Eyebrow text="RESUMO" />
      <h2 id="summary-heading" className="text-[30px] leading-[1.06] tracking-[-0.045em]">
        A tua compra
      </h2>
      <div className="relative my-6 grid gap-[7px] overflow-hidden border-l-4 border-acento-principal bg-azul-superficie px-5 py-6">
        <img
          src={eneiLogo}
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-[34px] -right-2 h-[142px] w-[62px] object-contain opacity-[0.06]"
        />
        <span className="text-[11px] text-cinza-texto">ENEI 2027</span>
        <strong>{tier?.name ?? "Escolhe uma modalidade"}</strong>
        <small className="text-[11px] text-cinza-texto">{EVENT_DATES} · Faro, Algarve</small>
      </div>
      <dl className={`m-0 grid gap-3 border-y ${BORDER} py-5`}>
        <div className="flex justify-between gap-[18px]">
          <dt className="text-cinza-texto">Quantidade</dt>
          <dd className="m-0 text-right">1</dd>
        </div>
        <div className="flex justify-between gap-[18px]">
          <dt className="text-cinza-texto">Subtotal</dt>
          <dd className="m-0 text-right">{price}</dd>
        </div>
        <div className="flex justify-between gap-[18px]">
          <dt className="text-cinza-texto">Taxas</dt>
          <dd className="m-0 text-right">Incluídas</dd>
        </div>
      </dl>
      <div className="flex justify-between gap-[18px] py-[22px] text-lg">
        <span>Total</span>
        <strong className="text-acento-forte">{price}</strong>
      </div>
      <ul className="m-0 mb-6 grid list-none gap-2.5 p-0 text-xs text-cinza-texto">
        {[
          "Preço com IVA incluído",
          "Um bilhete por pessoa",
          "Pagamento através de MB Way",
          "Bilhete disponível na área pessoal",
        ].map((item) => (
          <li key={item} className="relative pl-[22px]">
            <span aria-hidden="true" className="absolute left-0 font-bold text-acento-forte">
              ✓
            </span>
            {item}
          </li>
        ))}
      </ul>
      <Link to="/informacao-ajuda" className={`${linkClass} text-xs font-bold`}>
        Precisas de ajuda?
      </Link>
    </aside>
  );
}

function MbwayCard() {
  return (
    <div className={`my-7 mb-6 grid grid-cols-[auto_1fr] items-center gap-4 border ${BORDER} bg-azul-superficie p-[18px]`}>
      <div className="flex h-[54px] w-[92px] items-center justify-center rounded-[7px] bg-white px-2.5 py-[7px]">
        <img src={mbwayLogo} alt="MB Way" width={112} height={70} className="size-full object-contain" />
      </div>
      <div className="grid gap-[3px]">
        <strong>Pagamento seguro</strong>
        <span className="text-xs text-cinza-texto">Confirma a operação na aplicação MB Way.</span>
      </div>
    </div>
  );
}

/** Sem sessão: o bilhete fica associado a uma conta (ui-ux/bilhetes/checkout/conta). */
function AccountRequired() {
  const location = useLocation();
  return (
    <section className="py-[clamp(48px,7vw,92px)]">
      <div className={`mx-auto w-[min(calc(100%-28px),760px)] ${panelClass} px-[22px] py-[30px] min-[621px]:w-[min(calc(100%-40px),760px)] min-[621px]:p-[clamp(38px,6vw,64px)]`}>
        <Eyebrow text="CONTA_NECESSÁRIA" />
        <h2 className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
          Precisamos de associar o bilhete a uma conta.
        </h2>
        <p className="mt-3.5 text-cinza-texto">
          Cria uma conta ENEI para guardares o bilhete, receberes a confirmação por
          email e gerires a tua participação.
        </p>
        <div className="mt-7 grid gap-2.5 min-[621px]:grid-cols-2">
          <PrimaryButton text="Criar conta" to="/conta/criar" className="w-full" />
          <Link
            to="/conta"
            state={{ from: location }}
            className="inline-flex min-h-[46px] items-center justify-center rounded-full border border-white/25 bg-white/5 px-6 font-montserrat text-[14px] font-bold text-white transition hover:border-white/55"
          >
            Já tenho conta
          </Link>
        </div>
      </div>
    </section>
  );
}

/** Depois do 201: confirmar no telemóvel (ui-ux/bilhetes/checkout/aguardar). */
function AwaitingConfirmation({ transaction, tierName }: {
  transaction: Transaction;
  tierName: string;
}) {
  return (
    <section className="py-[clamp(48px,7vw,92px)]">
      <article
        aria-labelledby="status-title"
        aria-live="polite"
        className={`mx-auto grid w-[min(calc(100%-28px),640px)] justify-items-start gap-3 ${panelClass} px-[22px] py-[30px] min-[621px]:w-[min(calc(100%-40px),640px)] min-[621px]:p-[clamp(38px,6vw,56px)]`}
      >
        <div className="flex h-[54px] w-[92px] items-center justify-center rounded-[7px] bg-white px-2.5 py-[7px]">
          <img src={mbwayLogo} alt="MB Way" className="size-full object-contain" />
        </div>
        <span className="mt-3 font-montserrat text-[11px] font-bold tracking-[0.16em] text-acento-forte">
          A AGUARDAR
        </span>
        <h2 id="status-title" className="text-[clamp(32px,4vw,46px)] leading-[1.06] tracking-[-0.045em]">
          Confirma no MB Way
        </h2>
        <p className="m-0 text-cinza-texto">
          Enviámos um pedido de {formatCents(transaction.amount_cents, transaction.currency)} para
          o número terminado em {transaction.phone.slice(-3)}. Confirma o pagamento do bilhete{" "}
          <strong className="text-white">{tierName}</strong> na aplicação MB Way.
        </p>
        <dl className={`m-0 mt-2 grid w-full gap-3 border-y ${BORDER} py-5`}>
          <div className="flex justify-between gap-[18px]">
            <dt className="text-cinza-texto">Referência</dt>
            <dd className="m-0 font-bold">{transaction.reference}</dd>
          </div>
        </dl>
        <small className="text-cinza-texto">
          O pedido expira dentro de alguns minutos. Quando o pagamento for confirmado, o
          bilhete aparece na tua área pessoal.
        </small>
        <SecondaryButton text="Ir para a minha conta" to="/perfil" className="mt-3" />
      </article>
    </section>
  );
}

/* ------------------------------------------------------------------ */

export default function CheckoutPage() {
  usePageMeta("Checkout · ENEI 2027", "Compra o teu bilhete para o ENEI 2027 com MB Way.");

  const { user, loading: authLoading } = useAuth();
  const [params, setParams] = useSearchParams();
  const wanted = params.get("bilhete");
  // Modalidade pedida ao abrir a página; escolher outra muda o URL mas não recarrega.
  const [initialWanted] = useState(wanted);

  const [tiersState, setTiersState] = useState<TiersState>({ status: "loading" });
  const [selected, setSelected] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const [phoneTouched, setPhoneTouched] = useState(false);
  const [nif, setNif] = useState("");
  const [nifTouched, setNifTouched] = useState(false);
  const [terms, setTerms] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<CheckoutError | null>(null);
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const cooldown = useCooldown();

  // Lê as modalidades; `keepChoice` mantém a escolha se ainda se puder comprar.
  const loadTiers = useCallback(
    (keepChoice: string | null) =>
      fetchTicketTiers()
        .then((tiers) => {
          setTiersState({ status: "ready", tiers });
          setSelected(initialChoice(tiers, keepChoice));
        })
        .catch(() => setTiersState({ status: "error" })),
    [],
  );

  useEffect(() => {
    void loadTiers(initialWanted);
  }, [loadTiers, initialWanted]);

  const tiers = tiersState.status === "ready" ? tiersState.tiers : [];
  const selectedTier = tiers.find((t) => t.tier === selected) ?? null;
  const anyAvailable = tiers.some((t) => t.available);
  const phoneMsg = ptMobileError(phone);
  const shownPhoneError = error?.phoneError ?? (phoneTouched ? phoneMsg : null);
  const nifMsg = nifError(nif);
  const shownNifError = nifTouched ? nifMsg : null;

  const choose = (tier: string) => {
    setSelected(tier);
    setError(null);
    setParams({ bilhete: tier }, { replace: true });
  };

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting || cooldown.active) return;
    setPhoneTouched(true);
    setNifTouched(true);
    setError(null);

    if (!selectedTier || !selectedTier.available) {
      setError({ message: "Escolhe uma modalidade disponível." });
      return;
    }
    const normalized = normalizePtMobile(phone);
    if (!normalized || nifMsg) return; // o erro aparece junto ao campo
    if (!terms) {
      setError({ message: "Tens de aceitar os termos e a política de privacidade." });
      return;
    }

    setSubmitting(true);
    try {
      const tx = await initiatePayment(selectedTier.tier, normalized, cleanNif(nif) || undefined);
      rememberPaymentReference(tx.reference);
      setTransaction(tx);
      window.scrollTo({ top: 0, behavior: "instant" });
    } catch (err) {
      const mapped = checkoutErrorFor(err);
      setError(mapped);
      if (mapped.cooldownSeconds) cooldown.start(mapped.cooldownSeconds);
      if (mapped.action === "choose-tier") void loadTiers(selectedTier.tier);
    } finally {
      setSubmitting(false);
    }
  };

  const geral = tiers.find((t) => !t.is_student && t.available);

  return (
    <div className="min-h-screen bg-azul-base pt-16 font-poppins leading-[1.65] text-white min-[621px]:pt-[76px]">
      <div id="conteudo">
        <CheckoutHeading step={transaction ? 3 : 2} />

        {authLoading ? (
          <p role="status" className="py-24 text-center text-cinza-texto">
            A carregar...
          </p>
        ) : !user ? (
          <AccountRequired />
        ) : transaction ? (
          <AwaitingConfirmation
            transaction={transaction}
            tierName={selectedTier?.name ?? transaction.ticket_tier}
          />
        ) : (
          <section className="py-[clamp(56px,7vw,92px)]">
            <div className="mx-auto grid w-[min(calc(100%-28px),1180px)] items-start gap-7 min-[621px]:w-[min(calc(100%-40px),1180px)] min-[981px]:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.65fr)]">
              <form className="grid gap-6" onSubmit={handleSubmit} noValidate>
                {/* 01 · Bilhete */}
                <section aria-labelledby="ticket-heading" className={`${panelClass} px-[18px] py-6 min-[701px]:p-[clamp(26px,4vw,46px)]`}>
                  <PanelHeading
                    n="01"
                    eyebrow="BILHETE"
                    id="ticket-heading"
                    title="Escolhe a modalidade"
                    text="Seleciona a experiência que melhor se adapta a ti."
                  />

                  {tiersState.status === "loading" && (
                    <p role="status" className="mb-0 mt-7 text-cinza-texto">
                      A carregar as modalidades...
                    </p>
                  )}

                  {tiersState.status === "error" && (
                    <div role="alert" className="mt-7 grid justify-items-start gap-3">
                      <p className="m-0 text-red-400">
                        Não foi possível carregar as modalidades.
                      </p>
                      <SecondaryButton
                        text="Tentar novamente"
                        onClick={() => {
                          setTiersState({ status: "loading" });
                          void loadTiers(selected ?? wanted);
                        }}
                      />
                    </div>
                  )}

                  {tiersState.status === "ready" && (
                    <>
                      <fieldset className="m-0 mt-7 grid gap-3 border-0 p-0">
                        <legend className="sr-only">Modalidade do bilhete</legend>
                        {tiers.map((tier) => (
                          <TierOption
                            key={tier.tier}
                            tier={tier}
                            checked={tier.tier === selected}
                            onChange={choose}
                          />
                        ))}
                      </fieldset>
                      {!anyAvailable && (
                        <p role="status" className="mb-0 mt-5 border-l-[3px] border-acento-principal bg-[rgba(26,178,255,0.07)] px-3.5 py-3 text-sm text-gelo">
                          {tiers.some((t) => t.sale_open)
                            ? "De momento não há bilhetes disponíveis."
                            : "A bilheteira ainda não abriu."}
                        </p>
                      )}
                    </>
                  )}
                </section>

                {/* 02 · Pagamento */}
                <section aria-labelledby="payment-heading" className={`${panelClass} px-[18px] py-6 min-[701px]:p-[clamp(26px,4vw,46px)]`}>
                  <PanelHeading
                    n="02"
                    eyebrow="PAGAMENTO"
                    id="payment-heading"
                    title="Paga com MB Way"
                    text="Receberás um pedido de confirmação no telemóvel."
                  />

                  <MbwayCard />

                  <div className="grid gap-1.5">
                    <label htmlFor="phone" className="font-montserrat text-xs font-semibold text-gelo">
                      Número de telemóvel
                    </label>
                    <div
                      className={`grid grid-cols-[auto_minmax(0,1fr)] items-center rounded-[2px] border bg-azul-base focus-within:border-acento-principal focus-within:shadow-[0_0_0_3px_rgba(26,178,255,0.13)] ${
                        shownPhoneError ? "border-red-400" : BORDER
                      }`}
                    >
                      <span aria-hidden="true" className={`border-r ${BORDER} px-3.5 text-[13px] text-cinza-texto`}>
                        +351
                      </span>
                      <input
                        id="phone"
                        type="tel"
                        name="phone"
                        autoComplete="tel-national"
                        inputMode="tel"
                        placeholder="9XX XXX XXX"
                        maxLength={20}
                        value={phone}
                        onChange={(e) => {
                          setPhone(e.target.value);
                          if (error?.phoneError) setError(null);
                        }}
                        onBlur={() => setPhoneTouched(true)}
                        aria-invalid={shownPhoneError ? true : undefined}
                        aria-describedby={shownPhoneError ? "phone-error phone-help" : "phone-help"}
                        required
                        className="h-[52px] w-full min-w-0 border-0 bg-transparent px-4 text-white outline-none placeholder:text-cinza-subtil"
                      />
                    </div>
                    {shownPhoneError && (
                      <p id="phone-error" role="alert" className="m-0 text-[12px] text-red-400">
                        {shownPhoneError}
                      </p>
                    )}
                    <small id="phone-help" className="text-xs text-cinza-texto">
                      Utiliza o número associado à tua conta MB Way.
                    </small>
                  </div>

                  <div className="mt-[18px] grid gap-1.5">
                    <label htmlFor="nif" className="font-montserrat text-xs font-semibold text-gelo">
                      NIF <span className="font-normal text-cinza-texto">(opcional)</span>
                    </label>
                    <input
                      id="nif"
                      type="text"
                      name="nif"
                      inputMode="numeric"
                      autoComplete="off"
                      placeholder="123 456 789"
                      maxLength={14}
                      value={nif}
                      onChange={(e) => setNif(e.target.value)}
                      onBlur={() => setNifTouched(true)}
                      aria-invalid={shownNifError ? true : undefined}
                      aria-describedby={shownNifError ? "nif-error nif-help" : "nif-help"}
                      className={`h-[52px] w-full rounded-[2px] border bg-azul-base px-4 text-white outline-none placeholder:text-cinza-subtil focus:border-acento-principal focus:shadow-[0_0_0_3px_rgba(26,178,255,0.13)] ${
                        shownNifError ? "border-red-400" : BORDER
                      }`}
                    />
                    {shownNifError && (
                      <p id="nif-error" role="alert" className="m-0 text-[12px] text-red-400">
                        {shownNifError}
                      </p>
                    )}
                    <small id="nif-help" className="text-xs text-cinza-texto">
                      Preenche só se quiseres a fatura com o teu número de contribuinte.
                    </small>
                  </div>

                  <label className="my-[18px] inline-flex cursor-pointer items-start gap-[9px] text-sm text-cinza-texto">
                    <input
                      type="checkbox"
                      name="terms"
                      checked={terms}
                      onChange={(e) => setTerms(e.target.checked)}
                      required
                      className="mt-1 size-4 shrink-0 accent-acento-principal"
                    />
                    <span>
                      Confirmo que os dados da compra estão corretos e aceito os{" "}
                      <Link to="/termos" target="_blank" rel="noopener" className={linkClass}>
                        termos e condições
                      </Link>{" "}
                      e a{" "}
                      <Link to="/privacidade" target="_blank" rel="noopener" className={linkClass}>
                        política de privacidade
                      </Link>
                      .
                    </span>
                  </label>

                  {error && (
                    <div role="alert" className="mb-[18px] grid gap-1.5 text-[13px]">
                      <p className="m-0 text-red-400">{error.message}</p>
                      {error.action === "verify-email" && (
                        <Link to="/conta/verificar" state={{ email: user.email }} className={linkClass}>
                          Reenviar o email de verificação
                        </Link>
                      )}
                      {error.action === "student" && (
                        <p className="m-0 text-cinza-texto">
                          {geral ? (
                            <>
                              Podes escolher o{" "}
                              <button type="button" onClick={() => choose(geral.tier)} className={`${linkClass} underline`}>
                                {geral.name}
                              </button>{" "}
                              ou{" "}
                            </>
                          ) : (
                            "Podes "
                          )}
                          <Link to="/informacao-ajuda" className={linkClass}>
                            contactar a organização
                          </Link>
                          .
                        </p>
                      )}
                      {error.action === "account" && (
                        <Link to="/perfil" className={linkClass}>
                          Ver a minha conta
                        </Link>
                      )}
                    </div>
                  )}

                  <PrimaryButton
                    type="submit"
                    text={
                      submitting
                        ? "A iniciar o pagamento..."
                        : cooldown.active
                          ? `Aguarda ${cooldown.secondsLeft} s`
                          : "Pagar com MB Way →"
                    }
                    disabled={submitting || cooldown.active || !selectedTier || !anyAvailable}
                    aria-busy={submitting || undefined}
                    className="w-full !rounded-[2px]"
                  />
                </section>
              </form>

              <Summary tier={selectedTier} />
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
