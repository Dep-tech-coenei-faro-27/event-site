import { vi, test, expect, beforeEach } from 'vitest';
import { http } from '../src/utils/http';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers(),
    json: async () => ({}),
  });
  vi.stubGlobal('fetch', fetchMock);
});

test('envia credentials: include por omissão', async () => {
  await http('/auth/me');

  expect(fetchMock).toHaveBeenCalledWith(
    '/api/auth/me',
    expect.objectContaining({ credentials: 'include' }),
  );
});

test('credentials: include mesmo com outras opções', async () => {
  await http('/auth/login', { method: 'POST', body: { email: 'a@b.pt' } });

  expect(fetchMock).toHaveBeenCalledWith(
    '/api/auth/login',
    expect.objectContaining({ credentials: 'include', method: 'POST' }),
  );
});