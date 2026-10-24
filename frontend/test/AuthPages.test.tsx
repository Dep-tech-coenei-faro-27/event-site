import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import Login from '../src/pages/Login';
import Registo from '../src/pages/Registo';
import ForgotPassword from '../src/pages/ForgotPassword';
import ResetPassword from '../src/pages/ResetPassword';
import VerifyEmailPage from '../src/pages/VerifyEmailPage';
import UnverifiedAccount from '../src/pages/estados/UnverifiedAccount';
import LinkExpired from '../src/pages/estados/LinkExpired';
import TooManyAttempts from '../src/pages/estados/TooManyAttempts';
import { AuthProvider } from '../src/utils/AuthContext';
import { ApiError, NetworkError } from '../src/utils/http';

const mocks = vi.hoisted(() => ({ http: vi.fn(), onUnauthorized: { current: () => {} } }));
vi.mock('../src/utils/http', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../src/utils/http')>()),
  http: mocks.http,
  setUnauthorizedHandler: (fn: () => void) => {
    mocks.onUnauthorized.current = fn;
  },
}));

function Where() {
  return <div data-testid="where">{useLocation().pathname}</div>;
}

function WhereWithSearch() {
  const { pathname, search } = useLocation();
  return <div data-testid="where">{pathname + search}</div>;
}

const open = (entry: string | { pathname: string; search?: string; state?: unknown }) =>
  render(
    <MemoryRouter initialEntries={[entry]}>
      <main>
        <Routes>
          <Route path="/conta" element={<Login />} />
          <Route path="/conta/criar" element={<Registo />} />
          <Route path="/conta/recuperar" element={<ForgotPassword />} />
          <Route path="/conta/redefinir" element={<ResetPassword />} />
          <Route path="/conta/verificar" element={<VerifyEmailPage />} />
          <Route path="/conta/por-verificar" element={<UnverifiedAccount />} />
          <Route path="/conta/link-expirado" element={<LinkExpired />} />
          <Route path="/conta/demasiadas-tentativas" element={<TooManyAttempts />} />
          <Route path="*" element={<Where />} />
        </Routes>
      </main>
    </MemoryRouter>,
  );

const type = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

const PASSWORD = 'Segredo1!';

/** Um pedido que só termina quando o teste quiser. */
function deferred() {
  let resolve!: (value: unknown) => void;
  const promise = new Promise((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

beforeEach(() => {
  mocks.http.mockReset();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  document.body.removeAttribute('data-page');
  document.body.className = '';
});

type Page = {
  name: string;
  entry: string;
  path: string;
  button: string;
  busy: string;
  fill: () => void;
  /** O campo cujo valor tem de sobreviver a um erro. */
  kept: [label: string, value: string];
};

const pages: Page[] = [
  {
    name: 'Entrar',
    entry: '/conta',
    path: '/auth/login',
    button: 'Entrar na conta',
    busy: 'A entrar…',
    fill: () => {
      type('Email', 'ana@example.com');
      type('Palavra-passe', PASSWORD);
    },
    kept: ['Email', 'ana@example.com'],
  },
  {
    name: 'Criar conta',
    entry: '/conta/criar',
    path: '/auth/register',
    button: 'Criar conta',
    busy: 'A criar conta…',
    fill: () => {
      type('Nome completo', 'Ana Silva');
      type('Email', 'ana@example.com');
      type('Palavra-passe', PASSWORD);
      type('Confirmar palavra-passe', PASSWORD);
      fireEvent.click(screen.getByRole('checkbox'));
    },
    kept: ['Nome completo', 'Ana Silva'],
  },
  {
    name: 'Recuperar',
    entry: '/conta/recuperar',
    path: '/auth/forgot-password',
    button: 'Enviar ligação',
    busy: 'A enviar…',
    fill: () => type('Email', 'ana@example.com'),
    kept: ['Email', 'ana@example.com'],
  },
  {
    name: 'Redefinir',
    entry: '/conta/redefinir?token=abc',
    path: '/auth/reset-password',
    button: 'Guardar palavra-passe',
    busy: 'A guardar…',
    fill: () => {
      type('Nova palavra-passe', PASSWORD);
      type('Confirmar palavra-passe', PASSWORD);
    },
    kept: ['Nova palavra-passe', PASSWORD],
  },
  {
    name: 'Verificar email (reenvio)',
    entry: '/conta/verificar',
    path: '/auth/resend-verification-email',
    button: 'Reenviar email',
    busy: 'A enviar…',
    fill: () => type('Email da conta', 'ana@example.com'),
    kept: ['Email da conta', 'ana@example.com'],
  },
];

describe.each(pages)('$name: estados comuns', (page) => {
  const submit = () => fireEvent.click(screen.getByRole('button', { name: page.button }));

  test('desenho novo: um só h1 e o body marcado com data-page="conta"', () => {
    open(page.entry);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(document.body.dataset.page).toBe('conta');
    expect(document.querySelector('main .auth-shell .auth-card')).not.toBeNull();
  });

  test('a carregar: botão desativado e com indicação, e o duplo clique só envia um pedido', async () => {
    const request = deferred();
    mocks.http.mockReturnValue(request.promise);
    open(page.entry);
    page.fill();

    submit();
    const busy = screen.getByRole('button', { name: page.busy });
    expect(busy).toBeDisabled();
    expect(busy).toHaveAttribute('aria-busy', 'true');
    fireEvent.click(busy);
    fireEvent.submit(busy.closest('form')!);
    expect(mocks.http).toHaveBeenCalledTimes(1);
    expect(mocks.http.mock.calls[0][0]).toBe(page.path);

    await act(async () => request.resolve(null));
  });

  test('rede em baixo: diz-o, põe o foco no aviso e não apaga o que se escreveu', async () => {
    mocks.http.mockRejectedValue(new NetworkError());
    open(page.entry);
    page.fill();
    submit();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/não foi possível contactar o servidor/i);
    await waitFor(() => expect(alert).toHaveFocus());
    expect(screen.getByLabelText(page.kept[0])).toHaveValue(page.kept[1]);
    expect(screen.getByRole('button', { name: page.button })).toBeEnabled();
  });

  test('5xx: erro do servidor sem apagar o que se escreveu', async () => {
    mocks.http.mockRejectedValue(new ApiError(503, 'HTTP 503'));
    open(page.entry);
    page.fill();
    submit();

    expect(await screen.findByRole('alert')).toHaveTextContent(/erro no servidor/i);
    expect(screen.getByLabelText(page.kept[0])).toHaveValue(page.kept[1]);
  });

  test('429: mostra o tempo de espera do Retry-After', async () => {
    mocks.http.mockRejectedValue(new ApiError(429, 'HTTP 429', null, '30'));
    open(page.entry);
    page.fill();
    submit();

    expect(await screen.findByRole('alert')).toHaveTextContent(/tenta novamente dentro de 30 segundos/i);
    expect(screen.getByLabelText(page.kept[0])).toHaveValue(page.kept[1]);
  });
});

describe('Entrar', () => {
  test('campos com type e autocomplete certos', () => {
    open('/conta');
    expect(screen.getByLabelText('Email')).toHaveAttribute('type', 'email');
    expect(screen.getByLabelText('Email')).toHaveAttribute('autocomplete', 'email');
    expect(screen.getByLabelText('Palavra-passe')).toHaveAttribute('type', 'password');
    expect(screen.getByLabelText('Palavra-passe')).toHaveAttribute('autocomplete', 'current-password');
  });

  test('sucesso: envia os dados e segue para o perfil', async () => {
    vi.stubGlobal('location', { ...window.location, href: '/conta' });
    mocks.http.mockResolvedValue(null);
    open('/conta');
    pages[0].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Entrar na conta' }));

    await waitFor(() => expect(window.location.href).toBe('/perfil'));
    expect(mocks.http).toHaveBeenCalledWith('/auth/login', {
      method: 'POST',
      body: { email: 'ana@example.com', password: PASSWORD, remember_me: false },
    });
  });

  test('401: email ou palavra-passe inválidos, com o foco no aviso', async () => {
    mocks.http.mockRejectedValue(new ApiError(401, 'Invalid email or password'));
    open('/conta');
    pages[0].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Entrar na conta' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Email ou palavra-passe inválidos.');
    await waitFor(() => expect(alert).toHaveFocus());
    expect(screen.getByLabelText('Palavra-passe')).toHaveValue(PASSWORD);
  });

  test('403: leva à página de conta por verificar, com o email', async () => {
    mocks.http.mockRejectedValue(new ApiError(403, 'Email not verified'));
    open('/conta');
    pages[0].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Entrar na conta' }));

    expect(await screen.findByRole('heading', { name: /confirma o teu email para continuar/i })).toBeInTheDocument();
    expect(screen.getByText('ana@example.com')).toBeInTheDocument();
  });

  test('422: o erro aparece no campo, que fica inválido e com o foco', async () => {
    mocks.http.mockRejectedValue(
      new ApiError(422, 'HTTP 422', [{ type: 'value_error', loc: ['body', 'email'], msg: 'x' }]),
    );
    open('/conta');
    pages[0].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Entrar na conta' }));

    const email = screen.getByLabelText('Email');
    await waitFor(() => expect(email).toHaveAttribute('aria-invalid', 'true'));
    expect(email).toHaveAccessibleDescription('Indica um email válido.');
    await waitFor(() => expect(email).toHaveFocus());
  });
});

describe('Criar conta', () => {
  test('campos com type e autocomplete certos, e as regras ao vivo', () => {
    open('/conta/criar');
    expect(screen.getByLabelText('Nome completo')).toHaveAttribute('autocomplete', 'name');
    expect(screen.getByLabelText('Email')).toHaveAttribute('autocomplete', 'email');
    for (const label of ['Palavra-passe', 'Confirmar palavra-passe']) {
      expect(screen.getByLabelText(label)).toHaveAttribute('type', 'password');
      expect(screen.getByLabelText(label)).toHaveAttribute('autocomplete', 'new-password');
    }
    type('Palavra-passe', 'abc');
    expect(screen.getByText('Uma letra maiúscula').closest('li')).toHaveAttribute('data-ok', 'false');
    type('Palavra-passe', 'Abc');
    expect(screen.getByText('Uma letra maiúscula').closest('li')).toHaveAttribute('data-ok', 'true');
  });

  test('sucesso: segue para «Conta criada. Verifica o teu email.» com o email', async () => {
    mocks.http.mockResolvedValue(null);
    open('/conta/criar');
    pages[1].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    expect(await screen.findByRole('heading', { name: 'Conta criada. Verifica o teu email.' })).toBeInTheDocument();
    expect(screen.getByText('ana@example.com')).toBeInTheDocument();
    expect(mocks.http).toHaveBeenCalledWith('/auth/register', {
      method: 'POST',
      body: { name: 'Ana Silva', email: 'ana@example.com', password: PASSWORD, accept_terms: true },
    });
  });

  test('422 com ctx.rules: cada regra em falta aparece no campo da palavra-passe', async () => {
    mocks.http.mockRejectedValue(
      new ApiError(422, 'HTTP 422', [
        {
          type: 'password_invalid',
          loc: ['body', 'password'],
          msg: 'x',
          ctx: { rules: ['missing_digit', 'missing_symbol'] },
        },
      ]),
    );
    open('/conta/criar');
    pages[1].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    const password = screen.getByLabelText('Palavra-passe');
    await waitFor(() => expect(password).toHaveAttribute('aria-invalid', 'true'));
    expect(password).toHaveAccessibleDescription(/tem de incluir um número.*tem de incluir um símbolo/i);
    await waitFor(() => expect(password).toHaveFocus());
    expect(screen.getByLabelText('Nome completo')).toHaveValue('Ana Silva');
  });

  test('409: o email já usado aparece no campo do email', async () => {
    mocks.http.mockRejectedValue(new ApiError(409, 'A user with this email already exists'));
    open('/conta/criar');
    pages[1].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    const email = screen.getByLabelText('Email');
    await waitFor(() => expect(email).toHaveAccessibleDescription('Já existe uma conta com este email.'));
    await waitFor(() => expect(email).toHaveFocus());
  });

  test('erro da validação local: não pede nada e põe o foco no aviso', async () => {
    open('/conta/criar');
    pages[1].fill();
    type('Confirmar palavra-passe', 'Outra1!');
    fireEvent.click(screen.getByRole('button', { name: 'Criar conta' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('As palavras-passe não coincidem.');
    await waitFor(() => expect(alert).toHaveFocus());
    expect(mocks.http).not.toHaveBeenCalled();
  });
});

describe('Recuperar', () => {
  test('campo de email com type e autocomplete certos', () => {
    open('/conta/recuperar');
    expect(screen.getByLabelText('Email')).toHaveAttribute('type', 'email');
    expect(screen.getByLabelText('Email')).toHaveAttribute('autocomplete', 'email');
  });

  test('sucesso: confirma o envio sem dizer se a conta existe', async () => {
    mocks.http.mockResolvedValue(null);
    open('/conta/recuperar');
    pages[2].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Enviar ligação' }));

    expect(await screen.findByRole('status')).toHaveTextContent(/se existir uma conta com este email/i);
    expect(mocks.http).toHaveBeenCalledWith('/auth/forgot-password', {
      method: 'POST',
      body: { email: 'ana@example.com' },
    });
  });

  test('422: o erro aparece no campo do email', async () => {
    mocks.http.mockRejectedValue(
      new ApiError(422, 'HTTP 422', [{ type: 'email_not_ascii', loc: ['body', 'email'], msg: 'x' }]),
    );
    open('/conta/recuperar');
    pages[2].fill();
    fireEvent.click(screen.getByRole('button', { name: 'Enviar ligação' }));

    const email = screen.getByLabelText('Email');
    await waitFor(() => expect(email).toHaveAccessibleDescription(/só pode conter caracteres ascii/i));
    await waitFor(() => expect(email).toHaveFocus());
  });
});

describe('Redefinir', () => {
  const save = () => fireEvent.click(screen.getByRole('button', { name: 'Guardar palavra-passe' }));

  test('campos com type e autocomplete certos', () => {
    open('/conta/redefinir?token=abc');
    for (const label of ['Nova palavra-passe', 'Confirmar palavra-passe']) {
      expect(screen.getByLabelText(label)).toHaveAttribute('type', 'password');
      expect(screen.getByLabelText(label)).toHaveAttribute('autocomplete', 'new-password');
    }
  });

  test('sucesso: envia o token e diz para entrar com a nova palavra-passe', async () => {
    mocks.http.mockResolvedValue(null);
    open('/conta/redefinir?token=abc');
    pages[3].fill();
    save();

    expect(await screen.findByRole('heading', { name: 'Palavra-passe atualizada.' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Entrar na conta' })).toHaveAttribute('href', '/conta');
    expect(mocks.http).toHaveBeenCalledWith('/auth/reset-password', {
      method: 'POST',
      body: { token: 'abc', new_password: PASSWORD },
    });
  });

  test('sem token: vai para a página de ligação expirada', () => {
    open('/conta/redefinir');
    expect(screen.getByRole('heading', { name: 'Esta ligação já não está disponível.' })).toBeInTheDocument();
  });

  test('400 de ligação expirada ou usada: vai para a página de ligação expirada', async () => {
    mocks.http.mockRejectedValue(new ApiError(400, 'Reset token has expired'));
    open('/conta/redefinir?token=abc');
    pages[3].fill();
    save();

    expect(await screen.findByRole('heading', { name: 'Esta ligação já não está disponível.' })).toBeInTheDocument();
  });

  test('400 de palavra-passe igual à atual: o erro fica no campo', async () => {
    mocks.http.mockRejectedValue(
      new ApiError(400, 'New password must be different from your current password'),
    );
    open('/conta/redefinir?token=abc');
    pages[3].fill();
    save();

    const field = screen.getByLabelText('Nova palavra-passe');
    await waitFor(() => expect(field).toHaveAccessibleDescription(/diferente da atual/i));
    await waitFor(() => expect(field).toHaveFocus());
  });

  test('422 com ctx.rules: as regras em falta aparecem no campo da nova palavra-passe', async () => {
    mocks.http.mockRejectedValue(
      new ApiError(422, 'HTTP 422', [
        { type: 'password_invalid', loc: ['body', 'new_password'], msg: 'x', ctx: { rules: ['too_long'] } },
      ]),
    );
    open('/conta/redefinir?token=abc');
    pages[3].fill();
    save();

    const field = screen.getByLabelText('Nova palavra-passe');
    await waitFor(() => expect(field).toHaveAccessibleDescription(/demasiado longa/i));
    await waitFor(() => expect(field).toHaveFocus());
  });
});

describe('Verificar email', () => {
  test('com token: confirma a conta', async () => {
    mocks.http.mockResolvedValue(null);
    open('/conta/verificar?token=abc');
    expect(screen.getByRole('heading', { name: 'A confirmar o teu email…' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Conta confirmada.' })).toBeInTheDocument();
    expect(mocks.http).toHaveBeenCalledWith('/auth/verify-email', { method: 'POST', body: { token: 'abc' } });
  });

  test('com token inválido (400): vai para a ligação expirada, que pede um novo email de verificação', async () => {
    mocks.http.mockRejectedValue(new ApiError(400, 'Invalid verification token'));
    open('/conta/verificar?token=abc');
    expect(await screen.findByRole('heading', { name: 'Esta ligação já não está disponível.' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Pedir novo email' })).toHaveAttribute('href', '/conta/verificar');
  });

  test('com token e 429: vai para demasiadas tentativas, com o tempo do Retry-After', async () => {
    mocks.http.mockRejectedValue(new ApiError(429, 'HTTP 429', null, '120'));
    open('/conta/verificar?token=abc');
    expect(await screen.findByRole('heading', { name: 'Precisamos de fazer uma pausa.' })).toBeInTheDocument();
    expect(screen.getByText('02:00')).toBeInTheDocument();
  });

  test.each([
    ['rede em baixo', new NetworkError()],
    ['5xx', new ApiError(503, 'Service Unavailable')],
  ])('com token e %s: diz que algo correu mal e deixa tentar outra vez', async (_, error) => {
    mocks.http.mockRejectedValue(error);
    open('/conta/verificar?token=abc');
    expect(await screen.findByRole('heading', { name: 'Algo correu mal.' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument();
  });

  test('reenvio sem email: o erro aparece no campo, com o foco', async () => {
    open('/conta/verificar');
    expect(screen.getByLabelText('Email da conta')).toHaveAttribute('autocomplete', 'email');
    fireEvent.click(screen.getByRole('button', { name: 'Reenviar email' }));

    const field = screen.getByLabelText('Email da conta');
    await waitFor(() => expect(field).toHaveAccessibleDescription('Indica o email da conta.'));
    await waitFor(() => expect(field).toHaveFocus());
    expect(mocks.http).not.toHaveBeenCalled();
  });

  test('reenvio com sucesso: confirma sem dizer se a conta existe', async () => {
    mocks.http.mockResolvedValue(null);
    open({ pathname: '/conta/verificar', state: { email: 'ana@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Reenviar email' }));

    expect(await screen.findByText(/se a conta estiver por verificar/i)).toBeInTheDocument();
    expect(mocks.http).toHaveBeenCalledWith('/auth/resend-verification-email', {
      method: 'POST',
      body: { email: 'ana@example.com' },
    });
  });
});

describe('sessão terminada', () => {
  test('o login vindo de ?sessao=terminada avisa que a sessão terminou, e o aviso sai ao entrar', async () => {
    mocks.http.mockReturnValue(deferred().promise);
    open('/conta?sessao=terminada');
    expect(screen.getByRole('status')).toHaveTextContent('A tua sessão terminou. Entra novamente.');

    type('Email', 'ana@example.com');
    type('Palavra-passe', PASSWORD);
    fireEvent.click(screen.getByRole('button', { name: 'Entrar na conta' }));
    await waitFor(() => expect(screen.queryByText(/a tua sessão terminou/i)).not.toBeInTheDocument());
  });

  test('o login sem ?sessao=terminada não mostra o aviso', () => {
    open('/conta');
    expect(screen.queryByText(/a tua sessão terminou/i)).not.toBeInTheDocument();
  });

  test('um 401 num pedido privado leva ao login com o aviso de sessão terminada', async () => {
    mocks.http.mockRejectedValue(new ApiError(401, 'Not authenticated'));
    render(
      <MemoryRouter initialEntries={['/perfil']}>
        <AuthProvider>
          <Routes>
            <Route path="*" element={<WhereWithSearch />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    act(() => mocks.onUnauthorized.current());
    expect(await screen.findByTestId('where')).toHaveTextContent('/conta?sessao=terminada');
  });
});
