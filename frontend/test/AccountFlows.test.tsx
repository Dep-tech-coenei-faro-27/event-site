import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CheckoutPage from '../src/pages/Checkout';
import Bilhetes from '../src/pages/Bilhetes';
import { AuthContext, type AuthContextValue } from '../src/utils/authContextValue';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const auth: AuthContextValue = {
  user: { id: 1, name: 'Ana Silva', email: 'ana@exemplo.pt', role: 'user', is_verified: true, qr_code: null },
  loading: false,
  error: null,
  refresh: async () => {},
  retry: async () => {},
  logout: async () => {},
};

function renderAt(path: string, element: React.ReactNode) {
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="*" element={element} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

test('cada bilhete leva ao checkout com a modalidade no URL', () => {
  renderAt('/bilhetes', <Bilhetes />);

  const hrefs = screen
    .getAllByRole('link', { name: 'Escolher bilhete' })
    .map((a) => a.getAttribute('href'));
  expect(hrefs).toEqual([
    '/bilhetes/checkout?bilhete=acesso',
    '/bilhetes/checkout?bilhete=refeicoes',
    '/bilhetes/checkout?bilhete=completo',
    '/bilhetes/checkout?bilhete=geral',
    '/bilhetes/checkout?bilhete=geral_refeicoes',
  ]);
});

test('o checkout mostra a modalidade escolhida', () => {
  renderAt('/bilhetes/checkout?bilhete=completo', <CheckoutPage />);
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Experiência completa');
});

test('o checkout com uma modalidade desconhecida pede para escolher outra', () => {
  renderAt('/bilhetes/checkout?bilhete=vip', <CheckoutPage />);
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Escolhe uma modalidade.');
});
