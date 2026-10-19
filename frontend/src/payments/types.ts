// Formas das respostas da API de pagamentos (ver docs/api-payments.md e docs/api-auth.md).
// Dinheiro sempre em cêntimos. As modalidades vêm de GET /payment/tiers e vão crescer:
// `tier` é um texto, não uma lista fixa, e nenhum nome nem preço fica escrito no código.

export type TransactionStatus =
  | "pending"
  | "confirmed"
  | "failed"
  | "expired"
  | "refund_due"
  | "refunded";

/** Estados em que o pagamento já não muda sozinho (o polling pára). */
export const FINAL_STATUSES: readonly TransactionStatus[] = [
  "confirmed",
  "failed",
  "expired",
  "refund_due",
  "refunded",
];

export type Tier = {
  tier: string;
  name: string;
  /** `null` enquanto a modalidade não tem preço (bilheteira fechada). */
  price_cents: number | null;
  currency: string;
  is_student: boolean;
  sale_open: boolean;
  /** `false` se está esgotada ou reservada por pagamentos à espera, ou a venda está fechada. */
  available: boolean;
};

export type Transaction = {
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
};

export type InitiateRequest = {
  ticket_tier: string;
  /** Telemóvel português; o backend aceita espaços e indicativo e normaliza. */
  phone: string;
};

export type AccountTicket = {
  reference: string;
  tier: string;
  tier_name: string;
  holder_name: string;
  paid_at: string | null;
};

export type AccountPendingPayment = {
  reference: string;
  tier: string;
  tier_name: string;
  amount_cents: number;
  expires_at: string;
};

export type AccountRefundDue = {
  reference: string;
  amount_cents: number;
};

/** O que `GET /users/me` diz sobre a compra. Os campos são `null` quando não se aplicam. */
export type StudentVerificationStatus = "pending" | "verified";

export type Account = {
  /** Se a conta já foi verificada como estudante (as modalidades de estudante só abrem então). */
  student_verification_status?: StudentVerificationStatus;
  qr_code: string | null;
  ticket: AccountTicket | null;
  pending_payment: AccountPendingPayment | null;
  refund_due: AccountRefundDue | null;
};
