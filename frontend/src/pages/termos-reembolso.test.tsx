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

  it("identifica quem vende: AAUalg, NIF e sede", () => {
    const text = renderTerms()?.textContent ?? "";
    expect(text).toMatch(/vendido pela AAUalg/i);
    expect(text).toContain("504035266");
    expect(text).toContain("Campus da Penha, Instituto Superior de Engenharia, Estrada da Penha, 8005-139 Faro");
  });

  it("o pedido de quem não pode vir é caso a caso, parcial, por email, aceite até 28 de fevereiro de 2027, sem transferência", () => {
    const section = renderTerms();
    const text = section?.textContent ?? "";
    expect(text).toMatch(/caso a caso/i);
    expect(text).toMatch(/reembolso parcial/i);
    expect(text).toMatch(/até 28 de fevereiro de 2027, inclusive/i);
    expect(text).toMatch(/a data que conta é a da nossa aceitação, e não a do teu pedido/i);
    expect(text).not.toMatch(/transfer/i);
    expect(section?.querySelector('a[href="mailto:geral@eneiconf.pt"]')).not.toBeNull();
  });

  it("depois de aceitar, avisa por email e devolve em até 10 dias úteis, sem mais prazos; a partir de 1 de março não há parciais", () => {
    const text = renderTerms()?.textContent ?? "";
    expect(text).toMatch(/avisamos-te por email da aceitação/i);
    expect(text).toMatch(/em até 10 dias úteis a contar da data da aceitação/i);
    expect(text).not.toMatch(/banco|alguns dias/i);
    expect(text).toMatch(/A partir de 1 de março de 2027 não aceitamos reembolsos parciais/i);
  });

  it("tem o endereço #cancelamento-e-reembolso (o checkout liga para ele) e consta do índice", () => {
    const section = renderTerms();
    expect(section?.id).toBe("cancelamento-e-reembolso");
    expect(screen.getByRole("link", { name: "Cancelamento e reembolso" })).toHaveAttribute("href", "#cancelamento-e-reembolso");
  });

  it("a versão dos termos sobe e a data é a da alteração", () => {
    renderTerms();
    expect(document.body.textContent).toMatch(/1\.1/);
    expect(document.querySelector('time[datetime="2026-11-06"]')).not.toBeNull();
  });
});
