// Tipos e chamadas da API de pagamentos (ver docs/api-payments.md).
import { http } from './http';

export interface TicketTier {
  tier: string;
  name: string;
  price_cents: number | null;
  currency: string;
  is_student: boolean;
  sale_open: boolean;
  available: boolean;
}

export type TransactionStatus =
  | 'pending'
  | 'confirmed'
  | 'failed'
  | 'expired'
  | 'refund_due'
  | 'refunded';

export interface Transaction {
  reference: string;
  ticket_tier: string;
  status: TransactionStatus;
  amount_cents: number;
  quantity: number;
  currency: string;
  phone: string;
  expires_at: string;
  confirmed_at: string | null;
  created_at: string;
}

// Até haver um endpoint para o pagamento em curso, a referência fica no sessionStorage
// para o ecrã de espera a poder consultar.
export const PAYMENT_REFERENCE_KEY = 'enei:payment-reference';

export const fetchTicketTiers = () => http<TicketTier[]>('/payment/tiers');

// O NIF é opcional (fatura com número de contribuinte) e só vai no pedido se for indicado.
export const initiatePayment = (ticketTier: string, phone: string, nif?: string) =>
  http<Transaction>('/payment/initiate', {
    method: 'POST',
    body: { ticket_tier: ticketTier, phone, ...(nif ? { nif } : {}) },
  });

export function rememberPaymentReference(reference: string) {
  try {
    sessionStorage.setItem(PAYMENT_REFERENCE_KEY, reference);
  } catch {
    // sem armazenamento (modo privado): o 409 leva a pessoa à conta
  }
}
