import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    expect(screen.getByRole("heading", { name: /o bilhete fica na tua conta/i })).toBeInTheDocument();
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

  it("antes da data de abertura todas as modalidades ficam fechadas e dizem quando abre (hora de Lisboa)", async () => {
    const closed = TIERS.map((t) => ({ ...t, sale_open: false, available: false, opens_at: "2026-11-02T09:00:00Z" }));
    mocks.getTiers.mockResolvedValue(closed);
    renderAt();

    await screen.findByRole("radio", { name: /passe geral/i });
    for (const radio of screen.getAllByRole("radio")) expect(radio).toBeDisabled();
    expect(screen.getAllByText("A bilheteira abre a 2 de novembro às 09:00.")).toHaveLength(closed.length);
    expect(screen.queryByText("Esgotado.")).toBeNull();
    expect(screen.getByRole("button", { name: /pagar com mb way/i })).toBeDisabled();
  });

  it("quem espera pela abertura não precisa de recarregar: à hora marcada a página volta a pedir as modalidades e abre-as", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const opensAt = new Date(Date.now() + 30_000).toISOString();
      const closed = TIERS.map((t) => ({ ...t, sale_open: false, available: false, opens_at: opensAt }));
      mocks.getTiers.mockResolvedValueOnce(closed).mockResolvedValue(TIERS);
      renderAt();
      const general = await screen.findByRole("radio", { name: /passe geral/i });
      expect(general).toBeDisabled();
      const callsBefore = mocks.getTiers.mock.calls.length;

      await vi.advanceTimersByTimeAsync(25_000); // ainda antes da hora: nenhum pedido
      expect(mocks.getTiers.mock.calls.length).toBe(callsBefore);
      await vi.advanceTimersByTimeAsync(10_000); // passa a hora (mais o atraso de 0 a 3 s)

      await waitFor(() => expect(screen.getByRole("radio", { name: /passe geral/i })).toBeEnabled());
      expect(mocks.getTiers.mock.calls.length).toBeGreaterThan(callsBefore);
      expect(screen.queryByText(/A bilheteira abre a/)).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("longe da abertura (dias) não faz pedidos de repetição", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const opensAt = new Date(Date.now() + 3 * 24 * 3600_000).toISOString();
      mocks.getTiers.mockResolvedValue(TIERS.map((t) => ({ ...t, sale_open: false, available: false, opens_at: opensAt })));
      renderAt();
      await screen.findByRole("radio", { name: /passe geral/i });
      const calls = mocks.getTiers.mock.calls.length;

      await vi.advanceTimersByTimeAsync(60 * 60_000); // uma hora

      expect(mocks.getTiers.mock.calls.length).toBe(calls);
    } finally {
      vi.useRealTimers();
    }
  });

  it("nos últimos 5 minutos antes da abertura não faz pedidos; faz um só à hora marcada", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    // O atraso depois da hora é aleatório (0 a 3 s, e de 3 a 6 s nas repetições): fixa-se no máximo para o teste
    // não depender da sorte (o primeiro pedido às 8,97 s e a repetição só depois dos 14 s).
    const random = vi.spyOn(Math, "random").mockReturnValue(0.99);
    try {
      const opensAt = new Date(Date.now() + 4 * 60_000).toISOString();
      mocks.getTiers.mockResolvedValue(TIERS.map((t) => ({ ...t, sale_open: false, available: false, opens_at: opensAt })));
      renderAt();
      await screen.findByRole("radio", { name: /passe geral/i });
      const calls = mocks.getTiers.mock.calls.length;

      await vi.advanceTimersByTimeAsync(3.9 * 60_000); // ainda fechada, a menos de 5 min
      expect(mocks.getTiers.mock.calls.length).toBe(calls);

      await vi.advanceTimersByTimeAsync(10_000); // passa a hora (mais o atraso de 0 a 3 s)
      expect(mocks.getTiers.mock.calls.length - calls).toBe(1);
    } finally {
      random.mockRestore();
      vi.useRealTimers();
    }
  });

  it("com o relógio do browser adiantado (o servidor ainda diz fechada) volta a tentar com pausas, não em ciclo", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const opensAt = new Date(Date.now() - 60_000).toISOString(); // para o browser já devia ter aberto
      mocks.getTiers.mockResolvedValue(TIERS.map((t) => ({ ...t, sale_open: false, available: false, opens_at: opensAt })));
      renderAt();
      await screen.findByRole("radio", { name: /passe geral/i });
      const calls = mocks.getTiers.mock.calls.length;

      await vi.advanceTimersByTimeAsync(60_000);

      const extra = mocks.getTiers.mock.calls.length - calls;
      expect(extra).toBeGreaterThanOrEqual(1);
      expect(extra).toBeLessThanOrEqual(22); // uma volta de 3 a 6 s: cerca de 10 a 20 pedidos por minuto
    } finally {
      vi.useRealTimers();
    }
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

  it("a ajuda do NIF diz que a fatura é manual e chega até 20 dias úteis depois da compra", async () => {
    renderAt();
    expect(await screen.findByText(/a fatura é emitida manualmente e enviada por email até 20 dias úteis após a compra/i)).toBeInTheDocument();
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

  it("o servidor recusa o NIF (regras mais estritas que o ecrã): avisa e fica no formulário", async () => {
    mocks.initiatePayment.mockRejectedValue(
      new ApiError(422, "x", [{ type: "value_error", loc: ["body", "nif"], msg: "nif does not start with a valid digit" }]),
    );
    renderAt();
    fireEvent.change(await screen.findByLabelText(/^NIF/i), { target: { value: "000000000" } });
    await fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent(/NIF não é válido/i);
    expect(screen.queryByTestId("where")).toBeNull();
  });

  it("esgotou entretanto: mostra o motivo e fica no formulário", async () => {
    mocks.initiatePayment.mockRejectedValue(new ApiError(409, "x", "This ticket tier is sold out"));
    renderAt();
    await fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent("Esta modalidade esgotou.");
    expect(screen.queryByTestId("where")).toBeNull();
  });

  it("403 de estudante: diz porquê, leva ao comprovativo e dá o contacto da organização", async () => {
    mocks.initiatePayment.mockRejectedValue(
      new ApiError(403, "x", "Student verification is required to buy this ticket"),
    );
    renderAt();
    await fillAndSubmit();
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/só para estudantes com a conta verificada/i);
    expect(within(alert).getByRole("link", { name: /enviar comprovativo de estudante/i })).toHaveAttribute(
      "href",
      "/perfil#comprovativo",
    );
    expect(within(alert).getByRole("link", { name: "geral@eneiconf.pt" })).toHaveAttribute("href", "mailto:geral@eneiconf.pt");
  });

  it("sem verificação de estudante aponta para o envio do comprovativo", async () => {
    renderAt();
    await screen.findByRole("radio", { name: /passe geral/i });
    expect(screen.getByRole("link", { name: "Enviar comprovativo" })).toHaveAttribute("href", "/perfil#comprovativo");
  });

  it("comprovativo em revisão: a modalidade de estudante fica fechada e diz porquê", async () => {
    mocks.getAccount.mockResolvedValue(account({ student_verification_status: "submitted" }));
    renderAt();
    expect(await screen.findByRole("radio", { name: /apenas acesso/i })).toBeDisabled();
    expect(screen.getByText(/disponível quando o teu comprovativo for aprovado/i)).toBeInTheDocument();
    expect(screen.getByText(/está em revisão/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /comprovativo/i })).toBeNull();
  });

  it("comprovativo recusado: a modalidade de estudante fica fechada e leva ao motivo", async () => {
    mocks.getAccount.mockResolvedValue(account({ student_verification_status: "rejected" }));
    renderAt();
    expect(await screen.findByRole("radio", { name: /apenas acesso/i })).toBeDisabled();
    expect(screen.getByText("O teu comprovativo foi recusado.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver o comprovativo" })).toHaveAttribute("href", "/perfil#comprovativo");
  });

  it("comprovativo aprovado: compra a modalidade de estudante sem aviso de verificação", async () => {
    mocks.getAccount.mockResolvedValue(account({ student_verification_status: "verified" }));
    mocks.initiatePayment.mockResolvedValue({ reference: "ENEI-EST" });
    renderAt("/bilhetes/checkout?bilhete=acesso");
    await waitFor(() => expect(screen.getByRole("radio", { name: /apenas acesso/i })).toBeChecked());
    expect(screen.queryByRole("link", { name: /comprovativo/i })).toBeNull();
    await fillAndSubmit();
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/bilhetes/checkout/aguardar"));
    expect(mocks.initiatePayment).toHaveBeenCalledWith({ ticket_tier: "acesso", phone: "912345678" });
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
