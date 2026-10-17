import { ApiError, NetworkError } from "../utils/http";
import { retryAfterMessage } from "../utils/RetryAfter";

// Traduz os erros de POST /payment/initiate para o que o checkout mostra e faz. Os textos de
// `detail` da API estão em inglês e servem para distinguir casos: o utilizador vê sempre o texto
// em português daqui (propostas em docs/api-payments.md, «O que o frontend mostra em cada erro»).

export type InitiateFailureKind =
  | "session-ended"
  | "email-unverified"
  | "student-required"
  | "sold-out"
  | "already-in-progress"
  | "invalid-input"
  | "rate-limited"
  | "gateway-failed"
  | "sales-closed"
  | "payments-off"
  | "no-connection"
  | "unknown";

/** O que a interface deve oferecer a seguir. */
export type InitiateAction =
  | "login"
  | "resend-verification"
  | "choose-another-tier"
  | "view-account"
  | "fix-field"
  | "wait-and-retry"
  | "retry"
  | "none";

export type InitiateFailure = {
  kind: InitiateFailureKind;
  message: string;
  action: InitiateAction;
  /** Só em `rate-limited`: segundos até se poder tentar outra vez (0 se o servidor não disse). */
  retryAfterSeconds?: number;
  /** Só em `invalid-input`: o campo em falta ou inválido, quando se sabe. */
  field?: "phone" | "ticket_tier";
};

const DETAIL = {
  emailUnverified: "Please verify your email address to continue.",
  studentRequired: "Student verification is required to buy this ticket",
  soldOut: "This ticket tier is sold out",
  alreadyInProgress: "You already have a ticket or a payment in progress",
  salesClosed: "Ticket sales are not open yet",
  paymentsOff: "Payments are currently disabled.",
} as const;

/** Segundos de um cabeçalho `Retry-After` (segundos ou data HTTP); 0 se não houver ou não valer. */
export function retryAfterSeconds(raw: string | null): number {
  if (!raw) return 0;
  let secs = Number(raw);
  if (!Number.isFinite(secs)) {
    const date = Date.parse(raw);
    secs = Number.isNaN(date) ? 0 : (date - Date.now()) / 1000;
  }
  return secs > 0 ? Math.ceil(secs) : 0;
}

function invalidInput(detail: unknown): InitiateFailure {
  const items = Array.isArray(detail) ? (detail as { loc?: (string | number)[] }[]) : [];
  const fields = items.map((item) => String(item.loc?.[item.loc.length - 1] ?? ""));
  if (fields.includes("phone")) {
    return {
      kind: "invalid-input",
      field: "phone",
      action: "fix-field",
      message: "Indica um telemóvel português válido (9 dígitos).",
    };
  }
  if (fields.includes("ticket_tier")) {
    return {
      kind: "invalid-input",
      field: "ticket_tier",
      action: "choose-another-tier",
      message: "Escolhe uma das modalidades disponíveis.",
    };
  }
  return {
    kind: "invalid-input",
    action: "fix-field",
    message: "Os dados do pedido não são válidos. Confirma-os e tenta outra vez.",
  };
}

const NO_CONNECTION: InitiateFailure = {
  kind: "no-connection",
  // Não se repete sozinho: o pedido pode ter chegado e haver um pagamento em curso. Um 409 no
  // pedido seguinte leva ao ecrã de espera.
  action: "retry",
  message: "Sem ligação. Verifica a rede e tenta outra vez.",
};

export function describeInitiateError(error: unknown): InitiateFailure {
  if (error instanceof NetworkError) return NO_CONNECTION;
  if (!(error instanceof ApiError)) {
    return { kind: "unknown", action: "retry", message: "Algo correu mal. Tenta outra vez." };
  }

  const { status, detail } = error;
  switch (status) {
    case 401:
      return {
        kind: "session-ended",
        action: "login",
        message: "A tua sessão terminou. Entra outra vez para continuar.",
      };
    case 403:
      if (detail === DETAIL.emailUnverified) {
        return {
          kind: "email-unverified",
          action: "resend-verification",
          message: "Confirma o teu email para poderes comprar.",
        };
      }
      if (detail === DETAIL.studentRequired) {
        return {
          kind: "student-required",
          action: "choose-another-tier",
          message: "Esta modalidade é para estudantes com a conta verificada.",
        };
      }
      break;
    case 409:
      // O mesmo código para dois casos: distinguem-se pelo `detail`. Nunca dizer «esgotado»
      // a quem já tem bilhete ou pagamento em curso.
      if (detail === DETAIL.soldOut) {
        return {
          kind: "sold-out",
          action: "choose-another-tier",
          message: "Esta modalidade esgotou.",
        };
      }
      if (detail === DETAIL.alreadyInProgress) {
        return {
          kind: "already-in-progress",
          action: "view-account",
          message: "Já tens um bilhete ou um pagamento em curso.",
        };
      }
      break;
    case 422:
      return invalidInput(detail);
    case 429:
      return {
        kind: "rate-limited",
        action: "wait-and-retry",
        retryAfterSeconds: retryAfterSeconds(error.retryAfter),
        message: retryAfterMessage(error.retryAfter),
      };
    case 502:
      // A transação fica `failed`, que não conta como pagamento em curso: pode tentar já.
      return {
        kind: "gateway-failed",
        action: "retry",
        message: "Não conseguimos iniciar o pagamento. Tenta outra vez.",
      };
    case 503:
      if (detail === DETAIL.salesClosed) {
        return {
          kind: "sales-closed",
          action: "none",
          message: "A bilheteira ainda não abriu.",
        };
      }
      if (detail === DETAIL.paymentsOff) {
        return {
          kind: "payments-off",
          action: "none",
          message: "Os pagamentos estão temporariamente indisponíveis.",
        };
      }
      break;
  }

  if (status >= 500) return NO_CONNECTION;
  return { kind: "unknown", action: "retry", message: "Algo correu mal. Tenta outra vez." };
}
