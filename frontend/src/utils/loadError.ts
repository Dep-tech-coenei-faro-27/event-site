import { ApiError, NetworkError } from "./http";
import { retryAfterMessage } from "./RetryAfter";

/** 401: sem sessão ou sessão terminada. Não é uma falha a mostrar: leva ao login. */
export const isUnauthorized = (error: unknown) => error instanceof ApiError && error.status === 401;

/**
 * 401 que o AuthProvider já tratou: levou ao login com «A tua sessão terminou». A página não deve
 * navegar outra vez, senão o seu `navigate('/conta')` apaga o aviso.
 */
export const isSessionEnded = (error: unknown) => error instanceof ApiError && error.sessionEnded;

/** O que dizer quando um pedido de leitura falha (rede, 5xx, 429…). Nunca diz «não há dados». */
export function loadErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) {
    return retryAfterMessage(error.retryAfter, "Demasiados pedidos.");
  }
  if (error instanceof NetworkError) {
    return "Não conseguimos ligar ao servidor. Confirma a ligação à internet e tenta novamente.";
  }
  return "O servidor não conseguiu responder. Tenta novamente daqui a pouco.";
}
