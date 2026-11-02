import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import ErrorBoundary from '../src/components/ErrorBoundary';

let shouldThrow = true;

function Page() {
  if (shouldThrow) throw new Error('falha de teste ao desenhar');
  return <p>Página carregada</p>;
}

beforeEach(() => {
  shouldThrow = true;
  // O React regista o erro apanhado; fica fora do relatório dos testes.
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test('um erro ao desenhar mostra o ecrã de erro em vez de deixar o site em branco', () => {
  render(
    <div>
      <nav>Menu do site</nav>
      <ErrorBoundary>
        <Page />
      </ErrorBoundary>
    </div>,
  );

  expect(screen.getByRole('alert')).toHaveTextContent('Não conseguimos abrir esta página.');
  expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Pedir ajuda' })).toHaveAttribute(
    'href',
    '/informacao-ajuda',
  );
  // O resto do layout continua lá.
  expect(screen.getByText('Menu do site')).toBeInTheDocument();
});

test('sem erro, mostra a página normalmente', () => {
  shouldThrow = false;

  render(
    <ErrorBoundary>
      <Page />
    </ErrorBoundary>,
  );

  expect(screen.getByText('Página carregada')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('«Tentar novamente» volta a desenhar a página', () => {
  render(
    <ErrorBoundary>
      <Page />
    </ErrorBoundary>,
  );
  expect(screen.getByRole('alert')).toBeInTheDocument();

  shouldThrow = false;
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));

  expect(screen.getByText('Página carregada')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('se o erro continua, o ecrã de erro volta', () => {
  render(
    <ErrorBoundary>
      <Page />
    </ErrorBoundary>,
  );

  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));

  expect(screen.getByRole('alert')).toBeInTheDocument();
});

test('mudar de página (resetKey) limpa o erro', () => {
  const { rerender } = render(
    <ErrorBoundary resetKey="/agenda">
      <Page />
    </ErrorBoundary>,
  );
  expect(screen.getByRole('alert')).toBeInTheDocument();

  shouldThrow = false;
  rerender(
    <ErrorBoundary resetKey="/equipa">
      <Page />
    </ErrorBoundary>,
  );

  expect(screen.getByText('Página carregada')).toBeInTheDocument();
});

test('na raiz da aplicação o ecrã tem o seu <main> e «Tentar novamente» recarrega', () => {
  const reload = vi.fn();
  vi.stubGlobal('location', { ...window.location, reload });

  render(
    <ErrorBoundary standalone>
      <Page />
    </ErrorBoundary>,
  );

  expect(screen.getByRole('main')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));
  expect(reload).toHaveBeenCalledTimes(1);
});

test('dentro da aplicação o ecrã não acrescenta um segundo <main>', () => {
  render(
    <ErrorBoundary>
      <Page />
    </ErrorBoundary>,
  );

  expect(screen.queryByRole('main')).not.toBeInTheDocument();
});
