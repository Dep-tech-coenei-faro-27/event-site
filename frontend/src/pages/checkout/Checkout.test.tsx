import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Account, Tier } from "../../payments/types";
import { ApiError, NetworkError } from "../../utils/http";
import Checkout from "./Checkout";

const mocks = vi.hoisted(() => ({
  getTiers: vi.fn(),
  getAccount: vi.fn(),
  initiatePayment: vi.fn(),
  user: { current: null as null | { name: string; email: string } },
}));

vi.mock("../../payments/api", () => ({
  getTiers: mocks.getTiers,
  getAccount: mocks.getAccount,
  initiatePayment: mocks.initiatePayment,
}));
vi.mock("../../utils/useAuth", () => ({
  useAuth: () => ({ user: mocks.user.current, loading: false }),
}));

const TIERS: Tier[] = [
  { tier: "acesso", name: "Apenas acesso", price_cents: 2500, currency: "EUR", is_student: true, sale_open: true, available: true },
  { tier: "geral", name: "Passe geral", price_cents: 5000, currency: "EUR", is_student: false, sale_open: true, available: true },
  { tier: "vip", name: "Esgotada", price_cents: 9000, currency: "EUR", is_student: false, sale_open: true, available: false },
];

const account = (extra: Partial<Account> = {}): Account => ({
  qr_code: null,
  ticket: null,
  pending_payment: null,
  refund_due: null,
  student_verification_status: "pending",
  ...extra,
});

function Where() {
  const { pathname } = useLocation();
  return <div data-testid="where">{pathname}</div>;
}

function renderAt(url = "/bilhetes/checkout") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/bilhetes/checkout" element={<Checkout />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mocks.user.current = { name: "Ana", email: "ana@example.com" };
  mocks.getTiers.mockResolvedValue(TIERS);
  mocks.getAccount.mockResolvedValue(account());
  mocks.initiatePayment.mockReset();
  sessionStorage.clear();
});
afterEach(() => {
  cleanup();
  document.body.removeAttribute("data-page");
});

const fillAndSubmit = async (phone = "912 345 678") => {
  fireEvent.change(await screen.findByLabelText(/número de telemóvel/i), { target: { value: phone } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: /pagar com mb way/i }));
};

describe("checkout", () => {
  it("sem sessão pede para criar conta ou entrar, e não mostra o formulário", () => {
    mocks.user.current = null;
    renderAt();
    expect(screen.getByRole("heading", { name: /antes de comprar, cria a tua conta/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Criar conta" })).toHaveAttribute("href", "/conta/criar");
    expect(screen.getByRole("link", { name: "Já tenho conta" })).toHaveAttribute("href", "/conta");
    expect(screen.queryByRole("button", { name: /pagar com mb way/i })).toBeNull();
    expect(mocks.getTiers).not.toHaveBeenCalled();
  });

  it("mostra as modalidades da API com preço, e fecha a de estudante e a esgotada", async () => {
    renderAt();
    const general = await screen.findByRole("radio", { name: /passe geral/i });
    expect(general).toBeEnabled();
    expect(screen.getByRole("radio", { name: /apenas acesso/i })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /esgotada/i })).toBeDisabled();
    expect(screen.getByText(/disponível quando a tua conta de estudante estiver verificada/i)).toBeInTheDocument();
    expect(screen.getByText("Esgotado.")).toBeInTheDocument();
    expect(general).toBeChecked(); // a primeira aberta
  });

  it("abre a modalidade de estudante a quem já está verificado, e respeita a escolhida no endereço", async () => {
    mocks.getAccount.mockResolvedValue(account({ student_verification_status: "verified" }));
    renderAt("/bilhetes/checkout?bilhete=acesso");
    const student = await screen.findByRole("radio", { name: /apenas acesso/i });
    await waitFor(() => expect(student).toBeEnabled());
    expect(student).toBeChecked();
  });

  it("a modalidade pedida no endereço mas fechada não fica escolhida", async () => {
    renderAt("/bilhetes/checkout?bilhete=acesso");
    expect(await screen.findByRole("radio", { name: /passe geral/i })).toBeChecked();
  });

  it("só deixa pagar com telemóvel português válido e os termos aceites", async () => {
    renderAt();
    const pay = await screen.findByRole("button", { name: /pagar com mb way/i });
    expect(pay).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/número de telemóvel/i), { target: { value: "123" } });
    fireEvent.click(screen.getByRole("checkbox"));
    expect(pay).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/número de telemóvel/i), { target: { value: "+351 912 345 678" } });
    expect(pay).toBeEnabled();
  });

  it("paga: manda só a modalidade e o telemóvel normalizado, guarda a referência e vai à espera", async () => {
    mocks.initiatePayment.mockResolvedValue({ reference: "ENEI-ABC" });
    renderAt();
    await fillAndSubmit("+351 912 345 678");
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/bilhetes/checkout/aguardar"));
    expect(mocks.initiatePayment).toHaveBeenCalledTimes(1);
    expect(mocks.initiatePayment).toHaveBeenCalledWith({ ticket_tier: "geral", phone: "912345678" });
    expect(sessionStorage.getItem("enei.payment.reference")).toBe("ENEI-ABC");
  });

  it("o NIF é opcional: sem NIF o pedido não o leva", async () => {
    mocks.initiatePayment.mockResolvedValue({ reference: "ENEI-ABC" });
    renderAt();
    await fillAndSubmit();
    await waitFor(() => expect(mocks.initiatePayment).toHaveBeenCalledTimes(1));
    expect(mocks.initiatePayment.mock.calls[0][0]).toEqual({ ticket_tier: "geral", phone: "912345678" });
  });

  it("com NIF válido manda-o só com os 9 algarismos", async () => {
    mocks.initiatePayment.mockResolvedValue({ reference: "ENEI-ABC" });
    renderAt();
    fireEvent.change(await screen.findByLabelText(/^NIF/i), { target: { value: "PT 123 456 789" } });
    await fillAndSubmit();
    await waitFor(() => expect(mocks.initiatePayment).toHaveBeenCalledTimes(1));
    expect(mocks.initiatePayment).toHaveBeenCalledWith({ ticket_tier: "geral", phone: "912345678", nif: "123456789" });
  });

  it("um NIF inválido avisa junto ao campo e não deixa pagar nem faz pedido", async () => {
    renderAt();
    const field = await screen.findByLabelText(/^NIF/i);
    fireEvent.change(field, { target: { value: "123456780" } });
    fireEvent.blur(field);
    expect(await screen.findByText(/este nif não é válido/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/número de telemóvel/i), { target: { value: "912 345 678" } });
    fireEvent.click(screen.getByRole("checkbox"));
    const pay = screen.getByRole("button", { name: /pagar com mb way/i });
    expect(pay).toBeDisabled();
    fireEvent.click(pay);
    expect(mocks.initiatePayment).not.toHaveBeenCalled();
    fireEvent.change(field, { target: { value: "" } });
    expect(pay).toBeEnabled();
  });

  it("esgotou entretanto: mostra o motivo e fica no formulário", async () => {
    mocks.initiatePayment.mockRejectedValue(new ApiError(409, "x", "This ticket tier is sold out"));
    renderAt();
    await fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent("Esta modalidade esgotou.");
    expect(screen.queryByTestId("where")).toBeNull();
  });

  it("falha de rede: avisa e não repete o pedido sozinho", async () => {
    mocks.initiatePayment.mockRejectedValue(new NetworkError());
    renderAt();
    await fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent(/sem ligação/i);
    expect(mocks.initiatePayment).toHaveBeenCalledTimes(1);
  });

  it("quem já tem bilhete vai para a conta", async () => {
    mocks.getAccount.mockResolvedValue(
      account({ ticket: { reference: "R", tier: "geral", tier_name: "Passe geral", holder_name: "Ana", paid_at: null } }),
    );
    renderAt();
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/perfil"));
  });

  it("não mostra o formulário enquanto não sabe se a pessoa já tem bilhete (sem piscar antes de ir para a conta)", async () => {
    let resolveAccount: (value: Account) => void = () => undefined;
    mocks.getAccount.mockReturnValue(new Promise<Account>((resolve) => (resolveAccount = resolve)));
    renderAt();
    await waitFor(() => expect(mocks.getAccount).toHaveBeenCalled());
    expect(screen.queryByRole("heading", { name: /escolhe a modalidade/i })).toBeNull();
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();

    resolveAccount(
      account({ ticket: { reference: "R", tier: "geral", tier_name: "Passe geral", holder_name: "Ana", paid_at: null } }),
    );
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/perfil"));
    expect(screen.queryByRole("heading", { name: /escolhe a modalidade/i })).toBeNull();
  });

  it("se a conta não carregar mostra o formulário e o aviso em vez de ficar à espera para sempre", async () => {
    mocks.getAccount.mockRejectedValue(new NetworkError());
    renderAt();
    expect(await screen.findByRole("heading", { name: /escolhe a modalidade/i })).toBeInTheDocument();
  });

  it("quem tem um pagamento à espera retoma-o em vez de pagar outra vez", async () => {
    mocks.getAccount.mockResolvedValue(
      account({
        pending_payment: { reference: "ENEI-WAIT", tier: "geral", tier_name: "Passe geral", amount_cents: 5000, expires_at: "2026-10-18T10:00:00Z" },
      }),
    );
    renderAt();
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/bilhetes/checkout/aguardar"));
    expect(sessionStorage.getItem("enei.payment.reference")).toBe("ENEI-WAIT");
  });
});
