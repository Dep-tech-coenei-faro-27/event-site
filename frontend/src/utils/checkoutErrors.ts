// O que o checkout mostra em cada erro de POST /api/payment/initiate.
// Os textos seguem a tabela «O que o frontend mostra» de docs/api-payments.md.
// O `detail` da API vem em inglês e só serve para distinguir os casos.
import { ApiError } from './http';
import { retryAfterMessage, retryAfterSeconds } from './RetryAfter';

export type CheckoutErrorAction =
  | 'verify-email' // reenviar o email de verificação
  | 'student' // sugerir o passe geral ou o contacto
  | 'choose-tier' // voltar à escolha de modalidade (e recarregar as modalidades)
  | 'account'; // já tem bilhete ou pagamento em curso: ver a conta

export interface CheckoutError {
  message: string;
  action?: CheckoutErrorAction;
  /** Erro do campo do telemóvel (422), mostrado junto ao campo. */
  phoneError?: string;
  /** Segundos com o botão desativado (429). */
  cooldownSeconds?: number;
}

const EMAIL_NOT_VERIFIED = 'Please verify your email address to continue.';
const STUDENT_REQUIRED = 'Student verification is required to buy this ticket';
const SOLD_OUT = 'This ticket tier is sold out';
const ALREADY_BUYING = 'You already have a ticket or a payment in progress';
const SALES_NOT_OPEN = 'Ticket sales are not open yet';

// 422: { detail: [{ loc: ["body", "phone"], ... }] }
function hasFieldError(detail: unknown, field: string): boolean {
  return (
    Array.isArray(detail) &&
    detail.some((item: { loc?: unknown[] }) => item?.loc?.[item.loc.length - 1] === field)
  );
}

export function checkoutErrorFor(err: unknown): CheckoutError {
  if (!(err instanceof ApiError)) {
    // Não repetir sozinho: o pedido pode ter chegado e haver um pagamento em curso.
    return { message: 'Sem ligação. Verifica a rede e tenta outra vez.' };
  }

  switch (err.status) {
    case 401:
      return { message: 'A tua sessão terminou. Entra outra vez para continuar.' };
    case 403:
      if (err.message === EMAIL_NOT_VERIFIED) {
        return {
          message: 'Confirma o teu email para poderes comprar.',
          action: 'verify-email',
        };
      }
      if (err.message === STUDENT_REQUIRED) {
        return {
          message: 'Esta modalidade é para estudantes com a conta verificada.',
          action: 'student',
        };
      }
      break;
    case 409:
      if (err.message === SOLD_OUT) {
        return { message: 'Esta modalidade esgotou.', action: 'choose-tier' };
      }
      if (err.message === ALREADY_BUYING) {
        return {
          message: 'Já tens um bilhete ou um pagamento em curso.',
          action: 'account',
        };
      }
      break;
    case 422: {
      if (hasFieldError(err.detail, 'phone')) {
        return {
          message: 'Verifica o número de telemóvel.',
          phoneError: 'Indica um telemóvel português válido, por exemplo 912 345 678.',
        };
      }
      return {
        message: 'Não foi possível validar a compra. Escolhe a modalidade e tenta outra vez.',
        action: 'choose-tier',
      };
    }
    case 429:
      return {
        message: retryAfterMessage(err.retryAfter, 'Demasiadas tentativas.'),
        cooldownSeconds: Math.ceil(retryAfterSeconds(err.retryAfter)) || 30,
      };
    case 502:
      return { message: 'Não conseguimos iniciar o pagamento. Tenta outra vez.' };
    case 503:
      return err.message === SALES_NOT_OPEN
        ? { message: 'A bilheteira ainda não abriu.' }
        : { message: 'Os pagamentos estão temporariamente indisponíveis.' };
  }

  if (err.status >= 500) {
    return { message: 'Sem ligação. Verifica a rede e tenta outra vez.' };
  }
  return { message: 'Ocorreu um erro. Tenta novamente.' };
}
