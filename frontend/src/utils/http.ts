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
    throw new NetworkError(); // nunca chama onUnauthorized (G-48)
  }

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const message = typeof data?.detail === 'string' ? data.detail : `HTTP ${res.status}`;

    
    const isFormError401 =
    path === '/auth/login' ||
    (path === '/auth/password' && data?.detail === 'Current password is incorrect');
    const noSession = data?.detail === 'Not authenticated. Missing access token cookie.';
    if (res.status === 401 && !isFormError401 && !noSession) onUnauthorized();

    throw new ApiError(res.status, message, data?.detail, res.headers.get('Retry-After'));
  }

  return (res.status === 204 ? null : await res.json()) as T;
}