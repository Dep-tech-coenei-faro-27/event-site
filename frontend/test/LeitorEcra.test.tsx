import { afterEach, beforeAll, describe, expect, test, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom';
import { useEffect, useState } from 'react';
import ScrollToTop from '../src/components/ScrollToTop';
import { MAIN_ID } from '../src/components/SkipLink';
import InformacaoAjuda from '../src/pages/InformacaoAjuda';
import TeamHero from '../src/components/equipa/TeamHero';
import Acessibilidade from '../src/pages/Acessibilidade';
import Privacidade from '../src/pages/Privacidade';
import Termos from '../src/pages/TermosCondicoes';
import ForgotPassword from '../src/pages/ForgotPassword';
import ResetPassword from '../src/pages/ResetPassword';

beforeAll(() => {
  window.scrollTo = () => {};
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

/** Página que só mostra o <h1> depois de «carregar», como as páginas de conta. */
function SlowPage() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setReady(true), 300);
    return () => clearTimeout(t);
  }, []);
  return ready ? <h1>Perfil carregado</h1> : <p>A carregar…</p>;
}

function renderApp() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <ScrollToTop />
      <nav>
        <Link to="/agenda">Agenda</Link>
        <Link to="/lenta">Lenta</Link>
        <Link to="/sem-titulo">Sem título</Link>
        <Link to="/#contacto">Contacto</Link>
      </nav>
      <main id={MAIN_ID} tabIndex={-1}>
        <Routes>
          <Route path="/" element={<><h1>Início</h1><section id="contacto"><h2>Contacto</h2></section></>} />
          <Route path="/agenda" element={<h1>Agenda do evento</h1>} />
          <Route path="/lenta" element={<SlowPage />} />
          <Route path="/sem-titulo" element={<p>Só texto</p>} />
        </Routes>
      </main>
    </MemoryRouter>,
  );
}

describe('mudança de página com leitor de ecrã', () => {
  test('no primeiro carregamento o foco não é mexido', () => {
    renderApp();
    expect(document.body).toHaveFocus();
  });

  test('ao seguir um link, o foco passa para o <h1> da nova página', () => {
    renderApp();
    fireEvent.click(screen.getByRole('link', { name: 'Agenda' }));
    expect(screen.getByRole('heading', { level: 1, name: 'Agenda do evento' })).toHaveFocus();
  });

  test('numa página que ainda carrega, espera pelo <h1>', async () => {
    vi.useFakeTimers();
    renderApp();
    fireEvent.click(screen.getByRole('link', { name: 'Lenta' }));
    await act(async () => vi.advanceTimersByTime(300));
    expect(screen.getByRole('heading', { level: 1, name: 'Perfil carregado' })).toHaveFocus();
  });

  test('sem <h1>, o foco vai para o <main>', () => {
    vi.useFakeTimers();
    renderApp();
    fireEvent.click(screen.getByRole('link', { name: 'Sem título' }));
    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByRole('main')).toHaveFocus();
  });
});

describe('ligação para uma secção', () => {
  test('o foco vai para a secção (#contacto)', () => {
    window.HTMLElement.prototype.scrollIntoView = () => {};
    window.ResizeObserver ??= class { observe() {} disconnect() {} unobserve() {} } as unknown as typeof ResizeObserver;
    renderApp();
    fireEvent.click(screen.getByRole('link', { name: 'Contacto' }));
    expect(document.getElementById('contacto')).toHaveFocus();
  });
});

describe('texto escondido só visualmente', () => {
  test('a pesquisa de Informação & Ajuda tem nome', () => {
    render(<MemoryRouter><InformacaoAjuda /></MemoryRouter>);
    expect(screen.getByRole('searchbox', { name: 'Pesquisar perguntas' })).toBeInTheDocument();
  });

  test('a descrição da fotografia da equipa chega ao leitor de ecrã', () => {
    render(<TeamHero />);
    const p = screen.getByText(/Fotografia da equipa organizadora/);
    expect(p).toHaveClass('sr-only');
    expect(p).not.toHaveClass('hidden');
  });
});

describe('título do separador', () => {
  test.each([
    ['Acessibilidade', Acessibilidade, 'Declaração de acessibilidade · ENEI 2027'],
    ['Privacidade', Privacidade, 'Política de privacidade · ENEI 2027'],
    ['Termos', Termos, 'Termos e condições · ENEI 2027'],
    ['Recuperar', ForgotPassword, 'Recuperar acesso · ENEI 2027'],
    ['Redefinir', ResetPassword, 'Nova palavra-passe · ENEI 2027'],
  ])('%s tem título próprio', (_name, Page, title) => {
    document.title = '';
    render(<MemoryRouter><Page /></MemoryRouter>);
    expect(document.title).toBe(title);
  });
});
