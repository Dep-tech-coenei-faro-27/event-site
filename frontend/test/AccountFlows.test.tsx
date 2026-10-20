import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ChangePasswordPage from '../src/pages/ChangePassword';
import Bilhetes from '../src/pages/Bilhetes';
import { AuthContext, type AuthContextValue } from '../src/utils/authContextValue';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const auth: AuthContextValue = {
  user: { id: 1, name: 'Ana Silva', email: 'ana@exemplo.pt', role: 'user', is_verified: true },
  loading: false,
  refresh: async () => {},
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

function fillPasswordForm(current: string, next: string) {
  fireEvent.change(screen.getByLabelText('Palavra-passe atual'), { target: { value: current } });
  fireEvent.change(screen.getByLabelText('Nova palavra-passe'), { target: { value: next } });
  fireEvent.change(screen.getByLabelText('Confirmar nova palavra-passe'), {
    target: { value: next },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Guardar nova palavra-passe' }));
}

test('alterar a palavra-passe envia PUT /auth/password e mostra a confirmação', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ message: 'Password changed successfully' }), { status: 200 }),
  );
  vi.stubGlobal('fetch', fetchMock);

  renderAt('/conta/alterar-palavra-passe', <ChangePasswordPage />);
  fillPasswordForm('Antiga#123', 'NovaSegura#456');

  expect(await screen.findByText('Palavra-passe alterada.')).toBeInTheDocument();
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toBe('/api/auth/password');
  expect(init.method).toBe('PUT');
  expect(JSON.parse(init.body)).toEqual({
    current_password: 'Antiga#123',
    new_password: 'NovaSegura#456',
  });
});

test('palavra-passe atual errada mostra o erro no formulário', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Current password is incorrect' }), { status: 401 }),
    ),
  );

  renderAt('/conta/alterar-palavra-passe', <ChangePasswordPage />);
  fillPasswordForm('Errada#123', 'NovaSegura#456');

  expect(await screen.findByRole('alert')).toHaveTextContent(
    'A palavra-passe atual está incorreta.',
  );
});

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
