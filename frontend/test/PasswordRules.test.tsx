import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Registo from '../src/pages/Registo';
import ResetPassword from '../src/pages/ResetPassword';
import Seguranca from '../src/pages/Seguranca';
import { AuthContext, type AuthContextValue } from '../src/utils/authContextValue';
import { failedPasswordRules, newPasswordError, passwordRules } from '../src/utils/passwordChange';
import { validationMessages } from '../src/utils/ValidationErrors';
import { renderRoute } from '../src/test/routes';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// O que `validate_password` (backend/app/core/security.py) devolve em `ctx.rules` para cada palavra-passe.
// Se as regras do backend mudarem, esta tabela tem de mudar com elas.
const BACKEND: [string, string[]][] = [
  ['abcdefgh', ['missing_uppercase', 'missing_digit', 'missing_symbol']],
  ['Abcdefgh', ['missing_digit', 'missing_symbol']],
  ['Abcdefg1', ['missing_symbol']],
  ['Abcdefg1!', []],
  ['Senha#abc', ['missing_digit']],
  ['école#123', ['missing_uppercase']],
  ['abcdef1 ', ['missing_uppercase']],
  ['Abcdéfgh1', []], // «é» não é ASCII, por isso conta como símbolo
  ['ÉCOLE#123', []],
  ['Ébène#١٢٣', []], // maiúscula e algarismos fora do ASCII
  ['Ⓐbcdef1!', []],
  ['ǅabcdef1!', ['missing_uppercase']], // «ǅ» é titlecase, não maiúscula
  ['Ab1!' + 'a'.repeat(68), []], // 72 bytes
  ['Ab1!' + 'a'.repeat(69), ['too_long']], // 73 bytes
  ['Ab1!' + 'é'.repeat(34), []], // 72 bytes
  ['Ab1!' + 'é'.repeat(35), ['too_long']], // 74 bytes
];

describe('as regras da palavra-passe são as do backend', () => {
  test.each(BACKEND)('%j → ctx.rules %j', (password, rules) => {
    expect(failedPasswordRules(password)).toEqual(rules);
  });

  test('cada regra do backend tem uma mensagem própria num 422', () => {
    for (const rule of ['too_long', 'missing_uppercase', 'missing_digit', 'missing_symbol']) {
      const [message] = validationMessages([{ type: 'password_invalid', ctx: { rules: [rule] } }]);
      expect(message).not.toBe('A palavra-passe não é válida.');
    }
  });

  test('cada regra que se mostra corresponde a uma regra do backend', () => {
    expect(passwordRules.map((rule) => rule.code)).toEqual([
      'too_short',
      'missing_uppercase',
      'missing_digit',
      'missing_symbol',
    ]);
  });

  test('o mínimo de 8 conta caracteres como o backend, não unidades UTF-16', () => {
    const minLength = passwordRules.find((rule) => rule.code === 'too_short')!;
    expect(minLength.test('Ab1!😀😀')).toBe(false); // 6 caracteres, 8 unidades UTF-16
    expect(minLength.test('Ab1!😀😀😀😀')).toBe(true);
  });

  test('aceita como número os algarismos que `str.isdigit()` aceita', () => {
    expect(failedPasswordRules('Abcdefg²')).toEqual([]); // «²» não é ASCII, por isso também é símbolo
    expect(failedPasswordRules('Abcdefg₉')).toEqual([]);
    expect(failedPasswordRules('Abcdefg①')).toEqual([]);
    expect(failedPasswordRules('Abcdefg½')).toEqual(['missing_digit']); // numérico, mas não algarismo
  });
});

describe('newPasswordError', () => {
  test('aceita até 72 bytes e recusa a partir daí', () => {
    expect(newPasswordError('Ab1!' + 'a'.repeat(68))).toBeNull();
    expect(newPasswordError('Ab1!' + 'a'.repeat(69))).toBe('A palavra-passe é demasiado longa.');
    expect(newPasswordError('Ab1!' + 'é'.repeat(35))).toBe('A palavra-passe é demasiado longa.');
  });

  test('recusa uma palavra-passe que não cumpre as regras', () => {
    expect(newPasswordError('abcdefgh')).toBe('A palavra-passe não cumpre todos os requisitos.');
  });
});

const auth: AuthContextValue = {
  user: { id: 1, name: 'Ana Silva', email: 'ana@exemplo.pt', role: 'user', is_verified: true, qr_code: null },
  loading: false,
  error: null,
  refresh: async () => {},
  retry: async () => {},
  logout: async () => {},
};

const pages = [
  { name: 'Registo', path: '/conta/criar', element: <Registo />, field: 'Palavra-passe', variant: 'conta' },
  {
    name: 'Redefinir',
    path: '/conta/redefinir?token=abc',
    element: <ResetPassword />,
    field: 'Nova palavra-passe',
    variant: 'conta',
  },
  { name: 'Segurança', path: '/conta/seguranca', element: <Seguranca />, field: 'Nova palavra-passe', variant: 'painel' },
];

const open = (path: string, element: React.ReactNode) =>
  render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>
    </AuthContext.Provider>,
  );

describe.each(pages)('$name mostra as regras ao vivo', ({ path, element, field, variant }) => {
  const rules = () => within(screen.getByRole('list', { name: /requisitos/i })).getAllByRole('listitem');

  test('a mesma lista de regras', () => {
    open(path, element);
    expect(rules()).toHaveLength(passwordRules.length);
    rules().forEach((li, i) => expect(li).toHaveTextContent(passwordRules[i].label));
  });

  test('marca as regras como o backend as avalia', () => {
    open(path, element);
    expect(rules().every((li) => li.getAttribute('data-ok') === 'false')).toBe(true);
    fireEvent.change(screen.getByLabelText(field), { target: { value: 'Ébène#١٢٣' } });
    expect(rules().map((li) => li.getAttribute('data-ok'))).toEqual(['true', 'true', 'true', 'true']);
  });

  test('diz aos leitores de ecrã se cada regra está cumprida', () => {
    open(path, element);
    rules().forEach((li) => expect(li).toHaveTextContent('(por cumprir)'));
    fireEvent.change(screen.getByLabelText(field), { target: { value: 'Abcdefgh' } });
    expect(rules().map((li) => li.textContent?.includes('(cumprido)'))).toEqual([true, true, false, false]);
  });

  test(`usa o desenho «${variant}»`, () => {
    open(path, element);
    const list = screen.getByRole('list', { name: /requisitos/i });
    const marks = list.querySelectorAll('[aria-hidden="true"]');
    if (variant === 'conta') {
      expect(list).toHaveClass('password-rules');
      expect(marks).toHaveLength(0);
    } else {
      expect(list).not.toHaveClass('password-rules');
      expect(marks).toHaveLength(passwordRules.length);
    }
  });
});

const forms = [
  {
    name: 'Registo',
    path: '/conta/criar',
    element: <Registo />,
    fill: (password: string) => {
      fireEvent.change(screen.getByLabelText('Nome completo'), { target: { value: 'Ana Silva' } });
      fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'ana@exemplo.pt' } });
      fireEvent.change(screen.getByLabelText('Palavra-passe'), { target: { value: password } });
      fireEvent.change(screen.getByLabelText('Confirmar palavra-passe'), { target: { value: password } });
      fireEvent.click(screen.getByRole('checkbox'));
      fireEvent.submit(screen.getByRole('button', { name: 'Criar conta' }).closest('form')!);
    },
  },
  {
    name: 'Redefinir',
    path: '/conta/redefinir?token=abc',
    element: <ResetPassword />,
    fill: (password: string) => {
      fireEvent.change(screen.getByLabelText('Nova palavra-passe'), { target: { value: password } });
      fireEvent.change(screen.getByLabelText('Confirmar palavra-passe'), { target: { value: password } });
      fireEvent.submit(screen.getByRole('button', { name: 'Guardar palavra-passe' }).closest('form')!);
    },
  },
];

describe.each(forms)('$name valida a palavra-passe antes de pedir à API', ({ path, element, fill }) => {
  const fetchMock = vi.fn();
  const start = () => {
    fetchMock.mockReset().mockResolvedValue(new Response(JSON.stringify({ message: 'ok' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    open(path, element);
  };

  test.each([
    ['abcdefgh', 'A palavra-passe não cumpre todos os requisitos.'],
    ['Ab1!' + 'a'.repeat(69), 'A palavra-passe é demasiado longa.'],
  ])('%j não chega a ser enviada', (password, message) => {
    start();
    fill(password);
    expect(screen.getByRole('alert')).toHaveTextContent(message);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  test('uma palavra-passe válida é enviada', async () => {
    start();
    fill('Ab1!' + 'a'.repeat(68));
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });
});

test('/conta/alterar-palavra-passe leva à Segurança', async () => {
  await renderRoute('/conta/alterar-palavra-passe');
  expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('Segurança da conta.');
  expect(screen.getByRole('button', { name: 'Alterar palavra-passe' })).toBeInTheDocument();
});
