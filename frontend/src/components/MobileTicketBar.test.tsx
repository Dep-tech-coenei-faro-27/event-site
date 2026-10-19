import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import MobileTicketBar from "./MobileTicketBar";

afterEach(cleanup);

const at = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <MobileTicketBar />
    </MemoryRouter>,
  );

describe("barra «Bilhetes» do telemóvel", () => {
  it("leva aos bilhetes nas páginas normais", () => {
    at("/sobre");
    expect(screen.getByRole("complementary", { name: "Bilhetes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Bilhetes" })).toHaveAttribute("href", "/bilhetes");
  });

  it.each(["/bilhetes", "/bilhetes/checkout", "/bilhetes/checkout/aguardar", "/conta/sessao-terminada", "/conta/link-expirado"])(
    "não aparece em %s (compra e estados do sistema)",
    (path) => {
      at(path);
      expect(screen.queryByRole("complementary", { name: "Bilhetes" })).toBeNull();
    },
  );

  it("aparece nas páginas de conta normais", () => {
    at("/conta");
    expect(screen.getByRole("complementary", { name: "Bilhetes" })).toBeInTheDocument();
  });
});
