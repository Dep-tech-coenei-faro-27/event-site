import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import mbwayLogo from "../../assets/mbway-logo.svg";
import { getAccount, getTiers, initiatePayment } from "../../payments/api";
import { describeInitiateError, type InitiateFailure } from "../../payments/errors";
import { saveReference } from "../../payments/reference";
import type { Account, Tier } from "../../payments/types";
import { useAuth } from "../../utils/useAuth";
import { useBodyPage } from "../../utils/useBodyPage";
import { usePageMeta } from "../../utils/usePageMeta";
import CheckoutAccountGate from "./CheckoutAccountGate";
import { cleanNif, nifError } from "../../utils/nif";
import { formatPrice, isPortuguesePhone, normalizePhone } from "./format";

/**
 * Checkout (`ui-ux/bilhetes/checkout`): escolher a modalidade e pagar com MB WAY. As modalidades,
 * os preços e o «esgotado» vêm de `GET /payment/tiers` (nada fica escrito aqui). Não repete o pedido
 * sozinho: uma falha de rede pode ter deixado um pagamento em curso, e a retoma faz-se pela conta.
 */
export default function Checkout() {
  useBodyPage("checkout");
  usePageMeta(
    "Finalizar a inscrição · ENEI 2027",
    "Escolhe a modalidade do bilhete e conclui o pagamento com MB WAY.",
  );

  const { user, loading } = useAuth();
  if (loading) return <div className="checkout-page" aria-busy="true" style={{ minHeight: "60vh" }} />;
  if (!user) return <CheckoutAccountGate />;
  return <CheckoutForm />;
}

function CheckoutForm() {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const wanted = search.get("bilhete");

  const [tiers, setTiers] = useState<Tier[] | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [phone, setPhone] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [phoneTouched, setPhoneTouched] = useState(false);
  const [nif, setNif] = useState("");
  const [nifTouched, setNifTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [failure, setFailure] = useState<InitiateFailure | null>(null);

  // As modalidades e a conta (para retomar uma compra que já existe).
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getTiers({ signal: controller.signal }), getAccount({ signal: controller.signal })])
      .then(([loadedTiers, loadedAccount]) => {
        setTiers(loadedTiers);
        setAccount(loadedAccount);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadFailed(true);
          void error;
        }
      });
    return () => controller.abort();
  }, []);

  const verifiedStudent = account?.student_verification_status === "verified";
  const isOpen = (tier: Tier) => tier.available && (!tier.is_student || verifiedStudent);

  // A modalidade escolhida por omissão: a pedida no endereço, se estiver aberta; senão a primeira aberta.
  const initial = useMemo(() => {
    if (!tiers) return null;
    const asked = tiers.find((tier) => tier.tier === wanted);
    if (asked && isOpen(asked)) return asked.tier;
    return tiers.find(isOpen)?.tier ?? null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tiers, wanted, verifiedStudent]);

  const current = tiers?.find((tier) => tier.tier === (selected ?? initial)) ?? null;
  const phoneValid = isPortuguesePhone(phone);
  const nifMessage = nifError(nif);
  const canSubmit = Boolean(current && isOpen(current) && phoneValid && !nifMessage && accepted && !submitting);

  if (account?.ticket) return <Navigate to="/perfil" replace />;
  if (account?.pending_payment) {
    saveReference(account.pending_payment.reference);
    return <Navigate to="/bilhetes/checkout/aguardar" replace />;
  }

  // Enquanto não se sabe se a pessoa já tem bilhete ou um pagamento à espera não se mostra o formulário: senão aparecia
  // durante um instante e logo a seguir a página saltava para o perfil ou para a espera (parecia um erro do site).
  if (!account && !loadFailed) return <div className="checkout-page" aria-busy="true" style={{ minHeight: "60vh" }} />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPhoneTouched(true);
    setNifTouched(true);
    if (!current || !canSubmit) return;
    setFailure(null);
    setSubmitting(true);
    try {
      const transaction = await initiatePayment({
        ticket_tier: current.tier,
        phone: normalizePhone(phone),
        ...(cleanNif(nif) ? { nif: cleanNif(nif) } : {}),
      });
      saveReference(transaction.reference);
      navigate("/bilhetes/checkout/aguardar");
    } catch (error) {
      const described = describeInitiateError(error);
      setFailure(described);
      // Já havia uma compra: leva a pessoa a ela em vez de a deixar presa no formulário.
      if (described.kind === "already-in-progress") {
        try {
          setAccount(await getAccount());
        } catch {
          // a mensagem e a ligação à conta ficam visíveis
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="checkout-page">
      <header className="checkout-heading">
        <div className="container">
          <Link className="checkout-back" to="/bilhetes">
            ← Voltar aos bilhetes
          </Link>
          <div className="checkout-heading__copy">
            <div>
              <p className="eyebrow">&lt;CHECKOUT /&gt;</p>
              <h1>Finaliza a tua inscrição.</h1>
            </div>
            <p className="lead">Escolhe o bilhete e conclui o pagamento através de MB Way.</p>
          </div>
          <ol className="checkout-steps" aria-label="Etapas da compra">
            <li className="checkout-step checkout-step--active">
              <span>01</span>
              <strong>Bilhete</strong>
            </li>
            <li className="checkout-step checkout-step--active">
              <span>02</span>
              <strong>Pagamento</strong>
            </li>
            <li className="checkout-step">
              <span>03</span>
              <strong>Confirmação</strong>
            </li>
          </ol>
        </div>
      </header>

      <section className="section checkout-section" id="selecao">
        <div className="container checkout-layout">
          <form className="checkout-form" onSubmit={onSubmit} noValidate>
            <section className="checkout-panel" aria-labelledby="ticket-heading">
              <div className="checkout-panel__heading">
                <span className="checkout-panel__number">01</span>
                <div>
                  <p className="eyebrow">BILHETE</p>
                  <h2 id="ticket-heading">Escolhe a modalidade</h2>
                  <p>Seleciona a experiência que melhor se adapta a ti.</p>
                </div>
              </div>

              {loadFailed && (
                <p role="alert" className="checkout-error">
                  Não conseguimos carregar as modalidades. Recarrega a página e tenta outra vez.
                </p>
              )}
              {!tiers && !loadFailed && <p aria-live="polite">A carregar as modalidades…</p>}

              {tiers && (
                <fieldset className="checkout-ticket-list">
                  <legend className="sr-only">Modalidade do bilhete</legend>
                  {tiers.map((tier) => {
                    const open = isOpen(tier);
                    const checked = tier.tier === (selected ?? initial);
                    return (
                      <label
                        key={tier.tier}
                        className={`checkout-ticket-option${checked ? " is-selected" : ""}`}
                        aria-disabled={!open}
                        style={open ? undefined : { opacity: 0.55, cursor: "not-allowed" }}
                      >
                        <input
                          type="radio"
                          name="ticket"
                          value={tier.tier}
                          checked={checked}
                          disabled={!open}
                          onChange={() => setSelected(tier.tier)}
                        />
                        <span className="checkout-ticket-option__marker"></span>
                        <span className="checkout-ticket-option__copy">
                          <small>{tier.is_student ? "ESTUDANTE" : "NÃO ESTUDANTE"}</small>
                          <strong>{tier.name}</strong>
                          <span>{tierNote(tier, verifiedStudent)}</span>
                        </span>
                        <span className="checkout-ticket-option__price">{formatPrice(tier.price_cents, tier.currency)}</span>
                      </label>
                    );
                  })}
                </fieldset>
              )}
            </section>

            <section className="checkout-panel" aria-labelledby="payment-heading">
              <div className="checkout-panel__heading">
                <span className="checkout-panel__number">02</span>
                <div>
                  <p className="eyebrow">PAGAMENTO</p>
                  <h2 id="payment-heading">Paga com MB Way</h2>
                  <p>Receberás um pedido de confirmação no telemóvel.</p>
                </div>
              </div>

              <div className="mbway-card">
                <div className="mbway-mark">
                  <img src={mbwayLogo} alt="MB Way" width="112" height="70" />
                </div>
                <div>
                  <strong>Pagamento seguro</strong>
                  <span>Confirma a operação na aplicação MB Way.</span>
                </div>
              </div>

              <label className="auth-field checkout-phone">
                <span>Número de telemóvel</span>
                <span className="checkout-phone__control">
                  <span aria-hidden="true">+351</span>
                  <input
                    type="tel"
                    name="phone"
                    autoComplete="tel"
                    inputMode="tel"
                    placeholder="9XX XXX XXX"
                    aria-describedby="phone-help"
                    aria-invalid={phoneTouched && !phoneValid}
                    required
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    onBlur={() => setPhoneTouched(true)}
                  />
                </span>
                <small id="phone-help">
                  {phoneTouched && !phoneValid
                    ? "Indica um telemóvel português válido (9 dígitos)."
                    : "Utiliza o número associado à tua conta MB Way."}
                </small>
              </label>

              <label className="auth-field checkout-nif">
                <span>NIF (opcional)</span>
                <input
                  type="text"
                  name="nif"
                  autoComplete="off"
                  inputMode="numeric"
                  placeholder="123 456 789"
                  maxLength={14}
                  aria-describedby="nif-help"
                  aria-invalid={nifTouched && Boolean(nifMessage)}
                  value={nif}
                  onChange={(event) => setNif(event.target.value)}
                  onBlur={() => setNifTouched(true)}
                />
                <small id="nif-help" role={nifTouched && nifMessage ? "alert" : undefined}>
                  {nifTouched && nifMessage
                    ? nifMessage
                    : "Preenche só se quiseres a fatura com o teu número de contribuinte."}
                </small>
              </label>

              <label className="auth-check checkout-consent">
                <input
                  type="checkbox"
                  name="terms"
                  required
                  checked={accepted}
                  onChange={(event) => setAccepted(event.target.checked)}
                />
                <span>
                  Confirmo que os dados da compra estão corretos e aceito os{" "}
                  <Link className="auth-legal-link" to="/termos">
                    termos e condições
                  </Link>{" "}
                  e a{" "}
                  <Link className="auth-legal-link" to="/privacidade">
                    política de privacidade
                  </Link>
                  .
                </span>
              </label>

              {failure && <FailureNotice failure={failure} />}

              <button className="btn btn--primary checkout-submit" type="submit" disabled={!canSubmit}>
                {submitting ? "A iniciar o pagamento…" : "Pagar com MB Way"}
                <span aria-hidden="true">→</span>
              </button>
            </section>
          </form>

          <aside className="checkout-summary" aria-labelledby="summary-heading">
            <p className="eyebrow">RESUMO</p>
            <h2 id="summary-heading">A tua compra</h2>
            <div className="checkout-summary__ticket">
              <span>ENEI 2027</span>
              <strong>{current?.name ?? "Escolhe uma modalidade"}</strong>
              <small>1–4 abril · Faro, Algarve</small>
            </div>
            <dl className="checkout-summary__details">
              <div>
                <dt>Quantidade</dt>
                <dd>1</dd>
              </div>
              <div>
                <dt>Subtotal</dt>
                <dd>{current ? formatPrice(current.price_cents, current.currency) : "—"}</dd>
              </div>
              <div>
                <dt>Taxas</dt>
                <dd>Incluídas</dd>
              </div>
            </dl>
            <div className="checkout-summary__total">
              <span>Total</span>
              <strong>{current ? formatPrice(current.price_cents, current.currency) : "—"}</strong>
            </div>
            <ul className="checkout-trust-list">
              <li>Pagamento através de MB Way</li>
              <li>Bilhete disponível na área pessoal</li>
            </ul>
            <Link className="checkout-help" to="/informacao-ajuda">
              Precisas de ajuda?
            </Link>
          </aside>
        </div>
      </section>
    </div>
  );
}

/** A linha por baixo do nome: o que falta para a modalidade estar aberta, ou o que ela é. */
function tierNote(tier: Tier, verifiedStudent: boolean): string {
  if (tier.price_cents === null || !tier.sale_open) return "A bilheteira ainda não abriu.";
  if (!tier.available) return "Esgotado.";
  if (tier.is_student && !verifiedStudent) return "Disponível quando a tua conta de estudante estiver verificada.";
  return tier.is_student ? "Modalidade para estudantes." : "Modalidade geral.";
}

/** O que correu mal ao iniciar o pagamento e o que fazer a seguir (os textos vêm de `errors.ts`). */
function FailureNotice({ failure }: { failure: InitiateFailure }) {
  return (
    <div role="alert" className="checkout-error">
      <p style={{ margin: 0 }}>{failure.message}</p>
      {failure.action === "login" && (
        <p style={{ margin: "8px 0 0" }}>
          <Link className="auth-legal-link" to="/conta">
            Entrar
          </Link>
        </p>
      )}
      {failure.action === "resend-verification" && (
        <p style={{ margin: "8px 0 0" }}>
          <Link className="auth-legal-link" to="/conta/verificar">
            Reenviar o email de verificação
          </Link>
        </p>
      )}
      {failure.action === "view-account" && (
        <p style={{ margin: "8px 0 0" }}>
          <Link className="auth-legal-link" to="/perfil">
            Ver a minha conta
          </Link>
        </p>
      )}
    </div>
  );
}
