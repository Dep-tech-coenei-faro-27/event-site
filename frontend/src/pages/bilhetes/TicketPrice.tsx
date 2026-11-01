import type { Tier } from "../../payments/types";
import { formatPrice } from "../checkout/format";
import type { TierPrices } from "./useTierPrices";

/** Há Early Bird quando o servidor envia um preço normal acima do preço em vigor. */
function isEarlyBird(tier: Tier | undefined): tier is Tier & { price_cents: number; normal_price_cents: number } {
  return (
    tier !== undefined &&
    tier.price_cents !== null &&
    tier.normal_price_cents !== null &&
    tier.normal_price_cents !== undefined &&
    tier.normal_price_cents > tier.price_cents
  );
}

/** O preço com os cêntimos e o € mais pequenos: «8» grande, «,38 €» pequeno. Os leitores de ecrã leem o valor inteiro. */
function Money({ cents }: { cents: number }) {
  const parts = new Intl.NumberFormat("pt-PT", { style: "currency", currency: "EUR" }).formatToParts(cents / 100);
  const whole = parts.filter((part) => part.type === "integer").map((part) => part.value).join("");
  const small = parts.filter((part) => part.type !== "integer").map((part) => part.value).join("");
  return (
    <span className="price-now">
      <span className="sr-only">{formatPrice(cents)}</span>
      <span aria-hidden="true">
        {whole}
        <span className="price-cents">{small}</span>
      </span>
    </span>
  );
}

export function EarlyBirdNotice({ prices }: { prices: TierPrices }) {
  if (prices === null || prices === "erro" || !Object.values(prices).some(isEarlyBird)) return null;
  return (
    <div className="eb-notice" role="note">
      <strong>Preços de lançamento</strong>
      <span>Depois, aplica-se o preço normal.</span>
    </div>
  );
}

export function TicketPrice({ prices, slug }: { prices: TierPrices; slug: string }) {
  if (prices === null) {
    return <div className="price price--stack" aria-busy="true"><span className="price-pending">A carregar o preço…</span></div>;
  }
  const tier = prices === "erro" ? undefined : prices[slug];
  if (tier === undefined) {
    return <div className="price price--stack"><span className="price-pending">Preço no passo seguinte</span></div>;
  }
  if (tier.price_cents === null) {
    return <div className="price price--stack"><span className="price-pending">{formatPrice(null)}</span></div>;
  }
  if (!isEarlyBird(tier)) {
    return (
      <div className="price price--stack">
        <Money cents={tier.price_cents} />
      </div>
    );
  }
  return (
    <div className="price price--stack">
      <span className="price-row">
        <Money cents={tier.price_cents} />
        <s className="price-was">
          <span className="sr-only">Preço normal </span>
          {formatPrice(tier.normal_price_cents)}
        </s>
      </span>
      <span className="price-meta">
        <span className="price-save">Poupas {formatPrice(tier.normal_price_cents - tier.price_cents)}</span>
        <span className="price-until">Preço de lançamento</span>
      </span>
    </div>
  );
}
