import { useEffect, useState } from "react";
import { getTiers } from "../../payments/api";
import type { Tier } from "../../payments/types";

/** As modalidades com o preço do servidor (`GET /payment/tiers`), por `tier`. `null` enquanto carrega; `"erro"` se falhou. */
export type TierPrices = Record<string, Tier> | null | "erro";

export function useTierPrices(): TierPrices {
  const [prices, setPrices] = useState<TierPrices>(null);
  useEffect(() => {
    const controller = new AbortController();
    getTiers({ signal: controller.signal })
      .then((tiers) => setPrices(Object.fromEntries(tiers.map((tier) => [tier.tier, tier]))))
      .catch(() => {
        if (!controller.signal.aborted) setPrices("erro");
      });
    return () => controller.abort();
  }, []);
  return prices;
}
