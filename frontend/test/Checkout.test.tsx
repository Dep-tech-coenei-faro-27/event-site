import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CheckoutPage from '../src/pages/Checkout';
import { checkoutErrorFor } from '../src/utils/checkoutErrors';
import { ApiError, NetworkError } from '../src/utils/http';
import { PAYMENT_REFERENCE_KEY, type TicketTier } from '../src/utils/payments';
import { AuthContext, type AuthContextValue } from '../src/utils/authContextValue';

const user: AuthContextValue['user'] = {
  id: 1,
  name: 'Ana Silva',
  email: 'ana@exemplo.pt',
  role: 'user',
  is_verified: true,
};

const tier = (over: Partial<TicketTier> & { tier: string; name: string }): TicketTier => ({
  price_cents: 4500,
  currency: 'EUR',
  is_student: true,
  sale_open: true,
  available: true,
  ...over,
});

const TIERS: TicketTier[] = [
  tier({ tier: 'acesso', name: 'Apenas acesso', price_cents: 2500 }),
  tier({ tier: 'refeicoes', name: 'Acesso + refeições', available: false }),
  tier({ tier: 'completo', name: 'Experiência completa', price_cents: 4500 }),
  tier({ tier: 'geral', name: 'Passe geral', price_cents: 5000, is_student: false }),
];

const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers });

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>;

function mockApi(initiate: Handler, tiers: TicketTier[] = TIERS) {
  const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
    if (url === '/api/payment/tiers') return json(tiers);
    if (url === '/api/payment/initiate') return initiate(url, init);
    throw new Error(`pedido inesperado: ${url}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderCheckout(path = '/bilhetes/checkout?bilhete=completo', who = user) {
  const auth: AuthContextValue = {
    user: who,
    loading: false,
    refresh: async () => {},
    logout: async () => {},
  };
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/bilhetes/checkout" element={<CheckoutPage />} />
          <Route path="/conta" element={<p>Página de login</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

async function fillAndPay(phone = '912 345 678') {
  await screen.findByRole('radio', { name: /Experiência completa/ });
  fireEvent.change(screen.getByLabelText('Número de telemóvel'), { target: { value: phone } });
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: /Pagar com MB Way/ }));
}

beforeEach(() => {
  vi.stubGlobal('scrollTo', () => {});
  sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('mostra as modalidades e os preços da API, com a do URL escolhida', async () => {
  mockApi(() => json({}));
  renderCheckout();

  const completo = await screen.findByRole('radio', { name: /Experiência completa/ });
  expect(completo).toBeChecked();
  expect(screen.getByRole('radio', { name: /Acesso \+ refeições/ })).toBeDisabled();
  expect(screen.getByText('Esgotado')).toBeInTheDocument();

  const summary = screen.getByRole('complementary', { name: 'A tua compra' });
  expect(within(summary).getByText('Experiência completa')).toBeInTheDocument();
  expect(within(summary).getAllByText('45,00 €')).toHaveLength(2); // subtotal e total
  // Um bilhete por pessoa: sem campo de quantidade.
  expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
});

test('mudar de modalidade atualiza o resumo', async () => {
  mockApi(() => json({}));
  renderCheckout();

  fireEvent.click(await screen.findByRole('radio', { name: /Passe geral/ }));
  const summary = screen.getByRole('complementary', { name: 'A tua compra' });
  expect(within(summary).getByText('Passe geral')).toBeInTheDocument();
  expect(within(summary).getAllByText('50,00 €')).toHaveLength(2);
});

test('um telemóvel inválido não chega à API', async () => {
  const fetchMock = mockApi(() => json({}));
  renderCheckout();

  await fillAndPay('212345678');

  expect(await screen.findByText(/telemóvel português/)).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalledWith('/api/payment/initiate', expect.anything());
});

test('paga: envia a modalidade e o número normalizado e mostra a referência', async () => {
  const fetchMock = mockApi(() =>
    json(
      {
        reference: 'ENEI-4F2A9C1D7B',
        ticket_tier: 'completo',
        status: 'pending',
        amount_cents: 4500,
        quantity: 1,
        currency: 'EUR',
        phone: '912345678',
        expires_at: '2026-10-09T10:04:32+00:00',
        confirmed_at: null,
        created_at: '2026-10-09T10:00:32+00:00',
      },
      201,
    ),
  );
  renderCheckout();

  await fillAndPay('+351 912 345 678');

  expect(await screen.findByRole('heading', { name: 'Confirma no MB Way' })).toBeInTheDocument();
  expect(screen.getByText('ENEI-4F2A9C1D7B')).toBeInTheDocument();
  expect(sessionStorage.getItem(PAYMENT_REFERENCE_KEY)).toBe('ENEI-4F2A9C1D7B');

  const call = fetchMock.mock.calls.find(([url]) => url === '/api/payment/initiate')!;
  expect(call[1].method).toBe('POST');
  // O preço nunca vai no pedido: é o servidor que o decide.
  expect(JSON.parse(call[1].body as string)).toEqual({ ticket_tier: 'completo', phone: '912345678' });
});

test('o botão fica desativado enquanto o pedido está a decorrer (duplo clique)', async () => {
  let release!: (r: Response) => void;
  const fetchMock = mockApi(() => new Promise<Response>((resolve) => (release = resolve)));
  renderCheckout();

  await fillAndPay();
  const button = screen.getByRole('button', { name: /A iniciar o pagamento/ });
  expect(button).toBeDisabled();
  fireEvent.click(button);

  const initiateCalls = () =>
    fetchMock.mock.calls.filter(([url]) => url === '/api/payment/initiate').length;
  expect(initiateCalls()).toBe(1);

  release(json({ detail: 'Payment could not be initiated. Please try again.' }, 502));
  expect(await screen.findByText('Não conseguimos iniciar o pagamento. Tenta outra vez.')).toBeInTheDocument();
  expect(initiateCalls()).toBe(1);
});

test('409 «já tens bilhete» não diz esgotado e leva à conta', async () => {
  mockApi(() => json({ detail: 'You already have a ticket or a payment in progress' }, 409));
  renderCheckout();

  await fillAndPay();

  expect(await screen.findByText('Já tens um bilhete ou um pagamento em curso.')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Ver a minha conta' })).toHaveAttribute('href', '/perfil');
});

test('429 desativa o botão durante o Retry-After', async () => {
  mockApi(() => json({ detail: 'Too many requests' }, 429, { 'Retry-After': '20' }));
  renderCheckout();

  await fillAndPay();

  expect(await screen.findByRole('button', { name: /Aguarda 20 s/ })).toBeDisabled();
});

test('bilheteira fechada: sem modalidades disponíveis e botão desativado', async () => {
  mockApi(
    () => json({}),
    TIERS.map((t) => ({ ...t, price_cents: null, sale_open: false, available: false })),
  );
  renderCheckout();

  expect(await screen.findByText('A bilheteira ainda não abriu.')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Pagar com MB Way/ })).toBeDisabled();
});

test('sem sessão pede para criar conta ou entrar', async () => {
  mockApi(() => json({}));
  renderCheckout('/bilhetes/checkout?bilhete=geral', null);

  expect(
    screen.getByRole('heading', { name: 'Precisamos de associar o bilhete a uma conta.' }),
  ).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Criar conta' })).toHaveAttribute('href', '/conta/criar');
  fireEvent.click(screen.getByRole('link', { name: 'Já tenho conta' }));
  await waitFor(() => expect(screen.getByText('Página de login')).toBeInTheDocument());
});

test.each([
  [403, 'Please verify your email address to continue.', 'Confirma o teu email para poderes comprar.', 'verify-email'],
  [403, 'Student verification is required to buy this ticket', 'Esta modalidade é para estudantes com a conta verificada.', 'student'],
  [409, 'This ticket tier is sold out', 'Esta modalidade esgotou.', 'choose-tier'],
  [409, 'You already have a ticket or a payment in progress', 'Já tens um bilhete ou um pagamento em curso.', 'account'],
  [502, 'Payment could not be initiated. Please try again.', 'Não conseguimos iniciar o pagamento. Tenta outra vez.', undefined],
  [503, 'Ticket sales are not open yet', 'A bilheteira ainda não abriu.', undefined],
  [503, 'Payments are currently disabled.', 'Os pagamentos estão temporariamente indisponíveis.', undefined],
])('erro %i «%s» → texto em português', (status, detail, message, action) => {
  const result = checkoutErrorFor(new ApiError(status, detail, detail));
  expect(result.message).toBe(message);
  expect(result.action).toBe(action);
});

test('422 do telemóvel aparece junto ao campo', () => {
  const detail = [{ type: 'value_error', loc: ['body', 'phone'], msg: 'x' }];
  expect(checkoutErrorFor(new ApiError(422, 'HTTP 422', detail)).phoneError).toBeTruthy();
});

test('sem rede não promete nada nem repete sozinho', () => {
  expect(checkoutErrorFor(new NetworkError()).message).toBe(
    'Sem ligação. Verifica a rede e tenta outra vez.',
  );
});

test('o NIF é opcional: sem NIF não vai no pedido', async () => {
  const fetchMock = mockApi(() => json({}, 502));
  renderCheckout();

  await fillAndPay();

  await screen.findByText('Não conseguimos iniciar o pagamento. Tenta outra vez.');
  const call = fetchMock.mock.calls.find(([url]) => url === '/api/payment/initiate')!;
  expect(JSON.parse(call[1].body as string)).not.toHaveProperty('nif');
});

test('com NIF válido, vai no pedido só com os algarismos', async () => {
  const fetchMock = mockApi(() => json({}, 502));
  renderCheckout();

  await screen.findByRole('radio', { name: /Experiência completa/ });
  fireEvent.change(screen.getByLabelText(/NIF/), { target: { value: '123 456 789' } });
  await fillAndPay();

  await screen.findByText('Não conseguimos iniciar o pagamento. Tenta outra vez.');
  const call = fetchMock.mock.calls.find(([url]) => url === '/api/payment/initiate')!;
  expect(JSON.parse(call[1].body as string).nif).toBe('123456789');
});

test('um NIF inválido não chega à API', async () => {
  const fetchMock = mockApi(() => json({}));
  renderCheckout();

  await screen.findByRole('radio', { name: /Experiência completa/ });
  fireEvent.change(screen.getByLabelText(/NIF/), { target: { value: '123456780' } });
  await fillAndPay();

  expect(await screen.findByText('Este NIF não é válido. Confirma os algarismos.')).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalledWith('/api/payment/initiate', expect.anything());
});
