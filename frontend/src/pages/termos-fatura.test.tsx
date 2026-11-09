import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import TermosCondicoes from "./TermosCondicoes";

afterEach(cleanup);

describe("Termos: a fatura", () => {
  it("a secção «Pagamentos» diz que a AAUalg emite a fatura à mão e a envia até 20 dias úteis depois da compra", () => {
    render(
      <MemoryRouter>
        <TermosCondicoes />
      </MemoryRouter>,
    );
    const text = screen.getByRole("heading", { name: "Pagamentos" }).closest("section")?.textContent ?? document.body.textContent ?? "";
    expect(text).toMatch(/fatura é emitida manualmente pela AAUalg/i);
    expect(text).toMatch(/até 20 dias úteis após a compra/i);
    expect(text).toMatch(/NIF/);
  });
});
