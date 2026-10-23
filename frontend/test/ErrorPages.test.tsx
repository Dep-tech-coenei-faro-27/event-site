import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../src/App';
import ErrorBoundary from '../src/components/ErrorBoundary';
import NotFound from '../src/pages/NotFound';
import ServerError from '../src/pages/ServerError';
import { useBodyPage } from '../src/utils/useBodyPage';

// Sem sessão: o AuthProvider pergunta por `/auth/me` e fica sem utilizador.
vi.mock('../src/utils/http', () => ({
  http: vi.fn(() => Promise.reject(new Error('sem sessão'))),
  setUnauthorizedHandler: vi.fn(),
}));

let shouldThrow = true;

function Page() {
  useBodyPage('agenda');
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
  document.body.removeAttribute('data-page');
  document.body.className = '';
  window.history.pushState({}, '', '/');
});

const openApp = (path: string) => {
  window.history.pushState({}, '', path);
  render(<App />);
};

describe('404', () => {
  test('tem o desenho novo: um só h1, o código e as ligações do protótipo', () => {
    render(
      <MemoryRouter>
        <main>
          <NotFound />
        </main>
      </MemoryRouter>,
    );

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Perdeste-te pelo caminho?');
    expect(screen.getByRole('complementary', { name: 'Detalhes do erro' })).toHaveTextContent('404');
    expect(screen.getByRole('link', { name: 'Voltar ao início' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Ver agenda' })).toHaveAttribute('href', '/agenda');
    expect(document.body.dataset.page).toBe('estado');
    expect(document.body).toHaveClass('system-state-page');
    expect(document.title).toBe('Página não encontrada · ENEI 2027');
  });

  test('aparece numa rota inexistente, dentro do layout', async () => {
    openApp('/esta-pagina-nao-existe');

    expect(await screen.findByRole('heading', { level: 1, name: 'Perdeste-te pelo caminho?' })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getAllByRole('main')).toHaveLength(1);
    expect(screen.getAllByRole('navigation').length).toBeGreaterThan(0);
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  test('não aparece numa rota que existe', async () => {
    openApp('/termos');

    expect(await screen.findAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.queryByText('Perdeste-te pelo caminho?')).not.toBeInTheDocument();
  });
});

describe('500', () => {
  test('tem o desenho novo: um só h1, o código e o tom de perigo', () => {
    render(<ServerError onRetry={() => {}} />);

    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Algo não correu como esperado.');
    expect(screen.getByRole('complementary', { name: 'Detalhes do erro' })).toHaveTextContent('500');
    expect(document.body.dataset.page).toBe('estado');
    expect(document.body).toHaveClass('system-state-page', 'system-state-page--danger');
  });

  test('é o ecrã do ErrorBoundary e deixa o resto do site intacto', () => {
    render(
      <div>
        <nav aria-label="Navegação principal">Menu do site</nav>
        <main>
          <ErrorBoundary>
            <Page />
          </ErrorBoundary>
        </main>
        <footer>Rodapé do site</footer>
      </div>,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('Algo não correu como esperado.');
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByText('Menu do site')).toBeInTheDocument();
    expect(screen.getByText('Rodapé do site')).toBeInTheDocument();
    expect(document.body.dataset.page).toBe('estado');
  });

  test('«Tentar novamente» limpa o erro e devolve o body à página', () => {
    render(
      <ErrorBoundary>
        <Page />
      </ErrorBoundary>,
    );
    expect(document.body).toHaveClass('system-state-page--danger');

    shouldThrow = false;
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));

    expect(screen.getByText('Página carregada')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(document.body.dataset.page).toBe('agenda');
    expect(document.body).not.toHaveClass('system-state-page');
  });
});
