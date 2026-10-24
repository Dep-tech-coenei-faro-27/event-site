const BASE = '/api';

export class ApiError extends Error {
  status: number;
  detail: unknown;
  retryAfter: string | null;
  /** O 401 já foi tratado como «sessão terminada» (o AuthProvider levou ao login). */
  sessionEnded = false;

  constructor(status: number, message: string, detail?: unknown, retryAfter: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

export class NetworkError extends Error {
  constructor() {
    super('network');
    this.name = 'NetworkError';
  }
}

type HttpOptions = Omit<RequestInit, 'body'> & { body?: unknown };

let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => {
  onUnauthorized = fn;
};

export async function http<T = unknown>(path: string, options: HttpOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: 'include', // envia sempre o cookie de sessão
      ...rest,
      headers: { 'Content-Type': 'application/json', ...headers },
      body: body === undefined || typeof body === 'string' ? body : JSON.stringify(body),
    });
  } catch {
    throw new NetworkError(); // nunca chama onUnauthorized
  }

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const message = typeof data?.detail === 'string' ? data.detail : `HTTP ${res.status}`;

    // 401 que não significa «sessão terminada»: erro do próprio formulário (login, palavra-passe
    // atual errada), visitante sem sessão (sem cookie) ou a verificação inicial da sessão em
    // `/auth/me`, que não deve atirar para o login quem só está a ver páginas públicas.
    const isFormError401 =
      path === '/auth/login' ||
      path === '/auth/me' ||
      (path === '/auth/password' && data?.detail === 'Current password is incorrect');
    const noSession = data?.detail === 'Not authenticated. Missing access token cookie.';
    const error = new ApiError(res.status, message, data?.detail, res.headers.get('Retry-After'));
    if (res.status === 401 && !isFormError401 && !noSession) {
      error.sessionEnded = true;
      onUnauthorized();
    }
    throw error;
  }

  return (res.status === 204 ? null : await res.json()) as T;
}