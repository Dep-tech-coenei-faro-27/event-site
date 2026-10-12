const BASE = '/api';

export class ApiError extends Error {
  status: number;
  detail: unknown;
  retryAfter: string | null;

  constructor(status: number, message: string, detail?: unknown, retryAfter: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

type HttpOptions = Omit<RequestInit, 'body'> & { body?: unknown };

let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => {
  onUnauthorized = fn;
};

export async function http<T = unknown>(path: string, options: HttpOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include', // envia sempre o cookie de sessão
    ...rest,
    headers: { 'Content-Type': 'application/json', ...headers },
    body: body === undefined || typeof body === 'string' ? body : JSON.stringify(body),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const message = typeof data?.detail === 'string' ? data.detail : `HTTP ${res.status}`;

    // 401 fora das rotas de auth = sessão terminada
    if (res.status === 401 && !path.startsWith('/auth/')) onUnauthorized();

    throw new ApiError(res.status, message, data?.detail, res.headers.get('Retry-After'));
  }

  return (res.status === 204 ? null : await res.json()) as T;
}