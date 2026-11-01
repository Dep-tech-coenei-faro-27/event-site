import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import TermosCondicoes from "./TermosCondicoes";

afterEach(cleanup);

function renderTerms() {
  render(
    <MemoryRouter>
      <TermosCondicoes />
    </MemoryRouter>,
  );
  return screen.getByRole("heading", { name: "Cancelamento e reembolso" }).closest("section");
}

describe("Termos: cancelamento e reembolso", () => {
  it("diz que com o bilhete emitido não há reembolso e que um erro nosso se devolve por inteiro", () => {
    const text = renderTerms()?.textContent ?? "";
    expect(text).toMatch(/não há direito a reembolso/i);
    expect(text).toMatch(/por um erro nosso/i);
    expect(text).toMatch(/valor total, automaticamente/i);
    expect(text).toMatch(/cancelado pela organização, devolvemos também o valor total/i);
  });

  it("o pedido de quem não pode vir é caso a caso, parcial, por email, sem prazo nem transferência", () => {
    const section = renderTerms();
    const text = section?.textContent ?? "";
    expect(text).toMatch(/caso a caso/i);
    expect(text).toMatch(/o reembolso é parcial/i);
    expect(text).not.toMatch(/\d+\s*dias antes|até \d+ dias|transfer/i);
    expect(section?.querySelector('a[href="mailto:geral@eneiconf.pt"]')).not.toBeNull();
  });

  it("tem o endereço #cancelamento-e-reembolso (o checkout liga para ele) e consta do índice", () => {
    const section = renderTerms();
    expect(section?.id).toBe("cancelamento-e-reembolso");
    expect(screen.getByRole("link", { name: "Cancelamento e reembolso" })).toHaveAttribute("href", "#cancelamento-e-reembolso");
  });

  it("a versão dos termos sobe e a data é a da alteração", () => {
    renderTerms();
    expect(document.body.textContent).toMatch(/1\.1/);
    expect(document.querySelector('time[datetime="2026-11-01"]')).not.toBeNull();
  });
});
