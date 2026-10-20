import { http } from "../utils/http";
import type { Account, InitiateRequest, Tier, Transaction } from "./types";

type HttpOptions = Parameters<typeof http>[1];

/** Modalidades com preço e se se podem comprar agora. Público (não precisa de sessão). */
export const getTiers = (options?: HttpOptions) => http<Tier[]>("/payment/tiers", options);

/**
 * Inicia o pagamento MB WAY. O preço e a quantidade (sempre 1) são do servidor: o cliente só
 * escolhe a modalidade e dá o telemóvel. Não se repete sozinho: uma falha de rede pode ter
 * deixado um pagamento em curso.
 */
export const initiatePayment = (request: InitiateRequest, options?: HttpOptions) =>
  http<Transaction>("/payment/initiate", { ...options, method: "POST", body: request });

/** Estado de um pagamento. Só o dono o vê (para os outros a referência não existe: 404). */
export const getTransaction = (reference: string, options?: HttpOptions) =>
  http<Transaction>(`/payment/transactions/${encodeURIComponent(reference)}`, options);

/** A conta: bilhete, pagamento à espera e reembolso a caminho. */
export const getAccount = (options?: HttpOptions) => http<Account>("/users/me", options);
