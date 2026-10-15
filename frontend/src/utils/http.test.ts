import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, NetworkError, http, setUnauthorizedHandler } from './http';

function reply(status: number, body: unknown, headers: Record<string, string> = {}) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json', ...headers },
    }),
  );
}

describe('http', () => {
  const onUnauthorized = vi.fn();

  beforeEach(() => {
    onUnauthorized.mockReset();
    setUnauthorizedHandler(onUnauthorized);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    setUnauthorizedHandler(() => {});
  });

  it('um 401 de sessão terminada chama o handler', async () => {
    vi.stubGlobal('fetch', () => reply(401, { detail: 'Invalid or expired token' }));

    await expect(http('/users/me')).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['/auth/login', 'Invalid email or password'],
    ['/auth/me', 'Invalid or expired token'],
    ['/auth/password', 'Current password is incorrect'],
    ['/users/me', 'Not authenticated. Missing access token cookie.'],
  ])('o 401 de %s (%s) não é «sessão terminada»', async (path, detail) => {
    vi.stubGlobal('fetch', () => reply(401, { detail }));

    await expect(http(path)).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('uma falha de rede lança NetworkError e nunca chama o handler', async () => {
    vi.stubGlobal('fetch', () => Promise.reject(new TypeError('Failed to fetch')));

    await expect(http('/users/me')).rejects.toBeInstanceOf(NetworkError);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('o ApiError leva o estado, o detalhe e o Retry-After', async () => {
    vi.stubGlobal('fetch', () =>
      reply(429, { detail: 'Too many requests' }, { 'Retry-After': '42' }),
    );

    const error = await http('/auth/login').catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(429);
    expect((error as ApiError).retryAfter).toBe('42');
  });
});
