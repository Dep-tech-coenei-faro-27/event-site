import { afterEach, beforeAll, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import App from '../src/App';

// A sessão expira a meio: `/auth/me` ainda conhece a pessoa, mas o pedido privado seguinte responde 401.
const user = { id: 1, name: 'Ana Silva', email: 'ana@exemplo.pt', role: 'user', is_verified: true, course: null, qr_code: null };

function json(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
}

beforeAll(() => {
  window.scrollTo = () => {};
  window.HTMLElement.prototype.scrollIntoView = () => {};
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  sessionStorage.clear();
  localStorage.clear();
});

describe('sessão terminada a meio (401)', () => {
  test.each(['/perfil', '/bilhetes/checkout/aguardar', '/bilhetes/checkout/sucesso'])(
    'em %s, o login diz «A tua sessão terminou»',
    async (path) => {
      vi.stubGlobal(
        'fetch',
        vi.fn((url: string) =>
          String(url).endsWith('/auth/me') ? json(200, user) : json(401, { detail: 'Token has expired' }),
        ),
      );
      window.history.replaceState(null, '', path);

      render(<App />);

      expect(await screen.findByText('A tua sessão terminou. Entra novamente.')).toBeInTheDocument();
      expect(window.location.pathname).toBe('/conta');
      // Depois de entrar outra vez, volta à página onde estava.
      expect(window.history.state?.usr?.from?.pathname).toBe(path);
    },
  );

  test('sem sessão nenhuma (sem cookie), o checkout leva ao login sem o aviso', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json(401, { detail: 'Not authenticated. Missing access token cookie.' })),
    );
    window.history.replaceState(null, '', '/bilhetes/checkout/sucesso');

    render(<App />);

    expect(await screen.findByRole('heading', { level: 1, name: /A tua experiência começa aqui/ })).toBeInTheDocument();
    expect(window.location.pathname).toBe('/conta');
    expect(screen.queryByText('A tua sessão terminou. Entra novamente.')).toBeNull();
  });
});
