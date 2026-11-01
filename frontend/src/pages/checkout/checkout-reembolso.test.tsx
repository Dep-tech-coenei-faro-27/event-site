import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Account, Tier } from "../../payments/types";
import Checkout from "./Checkout";

const mocks = vi.hoisted(() => ({ getTiers: vi.fn(), getAccount: vi.fn(), initiatePayment: vi.fn() }));

vi.mock("../../payments/api", () => ({
  getTiers: mocks.getTiers,
  getAccount: mocks.getAccount,
  initiatePayment: mocks.initiatePayment,
}));
vi.mock("../../utils/useAuth", () => ({
  useAuth: () => ({ user: { name: "Ana", email: "ana@example.com" }, loading: false }),
}));

const TIERS: Tier[] = [
  { tier: "acesso", name: "Apenas acesso", price_cents: 2500, currency: "EUR", is_student: true, sale_open: true, available: true },
];
const ACCOUNT: Account = {
  qr_code: null,
  ticket: null,
  pending_payment: null,
  refund_due: null,
  student_verification_status: "pending",
};

beforeEach(() => {
  mocks.getTiers.mockResolvedValue(TIERS);
  mocks.getAccount.mockResolvedValue(ACCOUNT);
  sessionStorage.clear();
});
afterEach(() => {
  cleanup();
  document.body.removeAttribute("data-page");
});

describe("checkout: condições de reembolso", () => {
  it("mostra por cima do botão de pagar que o bilhete não é reembolsável, com o email e a ligação aos termos", async () => {
    render(
      <MemoryRouter initialEntries={["/bilhetes/checkout"]}>
        <Routes>
          <Route path="/bilhetes/checkout" element={<Checkout />} />
        </Routes>
      </MemoryRouter>,
    );
    await screen.findByLabelText(/número de telemóvel/i);

    const note = document.querySelector(".checkout-refund-note");
    expect(note?.textContent).toMatch(/o bilhete não é reembolsável/i);
    expect(note?.textContent).toMatch(/erro nosso, devolvemos-te o valor total/i);
    expect(screen.getByRole("link", { name: "geral@eneiconf.pt" })).toHaveAttribute("href", "mailto:geral@eneiconf.pt");
    expect(screen.getByRole("link", { name: "Ver as condições" })).toHaveAttribute("href", "/termos#cancelamento-e-reembolso");

    const pay = screen.getByRole("button", { name: /pagar com mb way/i });
    expect(note?.compareDocumentPosition(pay)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });
});
