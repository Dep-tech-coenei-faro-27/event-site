import type { Tier } from "../../payments/types";

/** Há Early Bird quando o servidor envia um preço normal acima do preço em vigor. */
export function isEarlyBird(tier: Tier | undefined): tier is Tier & { price_cents: number; normal_price_cents: number } {
  return (
    tier !== undefined &&
    tier.price_cents !== null &&
    tier.normal_price_cents !== null &&
    tier.normal_price_cents !== undefined &&
    tier.normal_price_cents > tier.price_cents
  );
}
