import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TicketQr from '../src/components/TicketQr';
import '@testing-library/jest-dom/vitest';
describe('TicketQr', () => {
  it('desenha o SVG do QR e mostra o código exatamente como veio', () => {
    const sampleCode = 'ENEI27-EXEMPLO-0123456789abcdef0123456789abcdef';
    const { container } = render(<TicketQr code={sampleCode} />);

    // 1. Confirma que o SVG do QR Code foi gerado
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();

    // 2. Confirma que tem o aria-label acessível configurado
    expect(
      screen.getByRole('img', { name: /código qr do teu bilhete/i }),
    ).toBeInTheDocument();

    // 3. Confirma que o código em texto alternativo aparece sem alterações
    expect(screen.getByText(`Código · ${sampleCode}`)).toBeInTheDocument();
  });

  it('respeita o tamanho mínimo definido no estilo do SVG', () => {
    const { container } = render(<TicketQr code="ABC-123" size={160} />);
    const svg = container.querySelector('svg');

    expect(svg).toHaveStyle({ width: '160px' });
  });
});