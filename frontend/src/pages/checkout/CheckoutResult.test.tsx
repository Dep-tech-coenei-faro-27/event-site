import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PaymentWatch } from "../../payments/usePaymentPolling";
import CheckoutError from "./CheckoutError";
import CheckoutSuccess from "./CheckoutSuccess";
import CheckoutWaiting from "./CheckoutWaiting";

const mocks = vi.hoisted(() => ({
  getAccount: vi.fn(),
  watch: { current: null as unknown as PaymentWatch },
}));

vi.mock("../../payments/api", () => ({ getAccount: mocks.getAccount, getTransaction: vi.fn() }));
vi.mock("../../payments/usePaymentPolling", () => ({ usePaymentPolling: () => mocks.watch.current }));

const watch = (extra: Partial<PaymentWatch>): PaymentWatch => ({
  phase: "waiting",
  transaction: null,
  account: null,
  connectionLost: false,
  accountChecked: true,
  ...extra,
});

function Where() {
  const { pathname, state } = useLocation();
  return (
    <div>
      <div data-testid="where">{pathname}</div>
      <div data-testid="state">{JSON.stringify(state)}</div>
    </div>
  );
}

function renderRoutes(initial: string | { pathname: string; state: unknown }) {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/bilhetes/checkout/aguardar" element={<CheckoutWaiting />} />
        <Route path="/bilhetes/checkout/sucesso" element={<CheckoutSuccess />} />
        <Route path="/bilhetes/checkout/erro" element={<CheckoutError />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  sessionStorage.clear();
  sessionStorage.setItem("enei.payment.reference", "ENEI-TEST");
  mocks.watch.current = watch({});
  mocks.getAccount.mockReset();
});
afterEach(() => {
  cleanup();
  document.body.removeAttribute("data-page");
  document.body.className = "";
});

describe("espera do pagamento", () => {
  it("enquanto espera mostra a referência e o pedido ao MB WAY", () => {
    renderRoutes("/bilhetes/checkout/aguardar");
    expect(screen.getByRole("heading", { name: /confirma no mb way/i })).toBeInTheDocument();
    expect(screen.getByText("A AGUARDAR")).toBeInTheDocument();
    expect(screen.getByText("ENEI-TEST")).toBeInTheDocument();
    expect(document.body.dataset.page).toBe("checkout");
    expect(document.body).toHaveClass("payment-result-page");
  });

  it("depois do prazo diz «ainda a confirmar» e mantém o aviso para aprovar no MB WAY", () => {
    mocks.watch.current = watch({ phase: "confirming" });
    renderRoutes("/bilhetes/checkout/aguardar");
    expect(screen.getByText("AINDA A CONFIRMAR")).toBeInTheDocument();
    expect(screen.getByText(/aprova-o agora na aplicação mb way/i)).toBeInTheDocument();
    expect(screen.getByText(/o teu lugar continua reservado/i)).toBeInTheDocument();
  });

  it("avisa quando se perde a ligação sem dar o pagamento por perdido", () => {
    mocks.watch.current = watch({ connectionLost: true });
    renderRoutes("/bilhetes/checkout/aguardar");
    expect(screen.getByRole("status")).toHaveTextContent(/perdemos a ligação/i);
  });

  it("pagamento confirmado leva ao sucesso", async () => {
    mocks.watch.current = watch({ phase: "confirmed" });
    mocks.getAccount.mockResolvedValue({ qr_code: "q", ticket: { reference: "R", tier: "geral", tier_name: "Passe geral", holder_name: "Ana", paid_at: null } });
    renderRoutes("/bilhetes/checkout/aguardar");
    expect(await screen.findByRole("heading", { name: /o teu lugar está garantido/i })).toBeInTheDocument();
  });

  it.each(["failed", "expired", "refund_due", "not-found", "error"] as const)("%s leva ao erro com o estado", async (phase) => {
    mocks.watch.current = watch({ phase, accountChecked: false });
    renderRoutes("/bilhetes/checkout/aguardar");
    expect(await screen.findByText("Estado")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("sem referência guardada retoma pelo pagamento à espera da conta", async () => {
    sessionStorage.clear();
    mocks.getAccount.mockResolvedValue({
      qr_code: null,
      ticket: null,
      refund_due: null,
      pending_payment: { reference: "ENEI-RETOMA", tier: "geral", tier_name: "Passe geral", amount_cents: 5000, expires_at: "2026-10-18T10:00:00Z" },
    });
    renderRoutes("/bilhetes/checkout/aguardar");
    await waitFor(() => expect(sessionStorage.getItem("enei.payment.reference")).toBe("ENEI-RETOMA"));
  });

  it("sem referência e sem pagamento à espera volta ao checkout", async () => {
    sessionStorage.clear();
    mocks.getAccount.mockResolvedValue({ qr_code: null, ticket: null, pending_payment: null, refund_due: null });
    renderRoutes("/bilhetes/checkout/aguardar");
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/bilhetes/checkout"));
  });
});

describe("sucesso", () => {
  it("mostra a modalidade e a referência do bilhete, sem prometer email", async () => {
    mocks.getAccount.mockResolvedValue({ qr_code: "q", ticket: { reference: "ENEI-OK", tier: "geral", tier_name: "Passe geral", holder_name: "Ana", paid_at: null } });
    renderRoutes("/bilhetes/checkout/sucesso");
    expect(await screen.findByText("ENEI-OK")).toBeInTheDocument();
    expect(screen.getByText("Passe geral")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ver o meu bilhete/i })).toHaveAttribute("href", "/perfil");
    expect(document.body.textContent).not.toMatch(/enviámos a confirmação para o teu email/i);
  });

  it("quem chega sem bilhete volta aos bilhetes", async () => {
    mocks.getAccount.mockResolvedValue({ qr_code: null, ticket: null, pending_payment: null, refund_due: null });
    renderRoutes("/bilhetes/checkout/sucesso");
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/bilhetes"));
  });
});

describe("erro", () => {
  const at = (state: unknown) => renderRoutes({ pathname: "/bilhetes/checkout/erro", state });

  it("recusado ou expirado, conferida a conta: «Sem cobrança» e deixa tentar outra vez", () => {
    at({ phase: "failed", accountChecked: true });
    expect(screen.getByText("Sem cobrança")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /tentar novamente/i })).toHaveAttribute("href", "/bilhetes/checkout");
  });

  it("sem conseguir ver a conta NUNCA diz «sem cobrança»", () => {
    at({ phase: "expired", accountChecked: false });
    expect(screen.queryByText("Sem cobrança")).toBeNull();
    expect(screen.getByText("Por confirmar")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /tentar novamente/i })).toBeNull();
    expect(screen.getByRole("link", { name: /ver a minha conta/i })).toHaveAttribute("href", "/perfil");
  });

  it("reembolso a caminho: explica e não oferece pagar outra vez", () => {
    at({ phase: "refund_due", accountChecked: true });
    expect(screen.getByText("REEMBOLSO A CAMINHO")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /tentar novamente/i })).toBeNull();
  });

  it("referência desconhecida: «não encontrámos este pagamento», com saída para a conta", () => {
    at({ phase: "not-found" });
    expect(screen.getByRole("heading", { name: /não encontrámos este pagamento/i })).toBeInTheDocument();
    expect(screen.queryByText("Sem cobrança")).toBeNull();
  });

  it("sem estado (endereço aberto à mão) mostra o erro genérico", () => {
    renderRoutes("/bilhetes/checkout/erro");
    expect(screen.getByRole("heading", { name: /não foi possível pagar/i })).toBeInTheDocument();
  });
});

// O relógio do `act` não é preciso aqui; este import mantém o estilo dos outros testes.
void act;
