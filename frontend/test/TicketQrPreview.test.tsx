import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import TicketQr from '../src/components/TicketQr';
import '@testing-library/jest-dom/vitest';

const CODE = 'ENEI27.1234.Qm9yZW5kYWRvU2FsdA.kF3x9Zr2uV8wYtLq0pNs6aBcDeFgHiJkLmNoPqRsTuV';

afterEach(() => {
  cleanup();
  document.body.removeAttribute('style');
  vi.restoreAllMocks();
});

const openPreview = () => {
  fireEvent.click(screen.getByRole('button', { name: /ampliar o código qr/i }));
  return screen.getByRole('dialog');
};

describe('QR ampliado', () => {
  it('não está aberto até se clicar no QR', () => {
    render(<TicketQr code={CODE} />);
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('abre por cima da página com o mesmo código, sem o alterar', () => {
    render(<TicketQr code={CODE} />);
    const dialog = openPreview();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog.querySelector('svg')).not.toBeNull();
    // o QR grande é o mesmo código: o texto por baixo mantém-se e só há um
    expect(screen.getAllByText(`Código · ${CODE}`)).toHaveLength(1);
    // vive no body (não dentro do cartão), para nenhum ancestral lhe prender a posição
    expect(dialog.parentElement).toBe(document.body);
  });

  it('fecha com o X', () => {
    render(<TicketQr code={CODE} />);
    openPreview();
    fireEvent.click(screen.getByRole('button', { name: /fechar o qr ampliado/i }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('fecha com um clique fora do QR (no fundo escurecido)', () => {
    render(<TicketQr code={CODE} />);
    fireEvent.click(openPreview());
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('não fecha com um clique no próprio QR', () => {
    render(<TicketQr code={CODE} />);
    const dialog = openPreview();
    fireEvent.click(dialog.querySelector('svg')!);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('fecha com Esc', () => {
    render(<TicketQr code={CODE} />);
    openPreview();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('põe o foco no X ao abrir e devolve-o ao QR pequeno ao fechar', () => {
    render(<TicketQr code={CODE} />);
    const trigger = screen.getByRole('button', { name: /ampliar o código qr/i });
    fireEvent.click(trigger);
    expect(screen.getByRole('button', { name: /fechar o qr ampliado/i })).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(trigger).toHaveFocus();
  });

  it('deixa a página onde estava: não faz scroll e repõe o estilo do body ao fechar', () => {
    const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    document.body.style.paddingRight = '3px';
    render(<TicketQr code={CODE} />);
    openPreview();
    expect(document.body.style.overflow).toBe('hidden');
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(document.body.style.overflow).toBe('');
    expect(document.body.style.paddingRight).toBe('3px');
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it('um novo render com o QR aberto não estraga o estilo que se repõe no fecho', () => {
    const { rerender } = render(<TicketQr code={CODE} />);
    openPreview();
    rerender(<TicketQr code={CODE} className="outra-classe" />);
    rerender(<TicketQr code={CODE} className="outra-classe-ainda" />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(document.body.style.overflow).toBe('');
    expect(document.body.style.paddingRight).toBe('');
  });
});
