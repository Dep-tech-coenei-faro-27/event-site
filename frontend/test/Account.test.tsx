import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DadosPessoais from "../src/pages/DadosPessoais";
import Profile from "../src/pages/Profile";
import Seguranca from "../src/pages/Seguranca";
import type { User } from "../src/utils/authContextValue";
import { ApiError } from "../src/utils/http";

const mocks = vi.hoisted(() => ({
  http: vi.fn(),
  getMe: vi.fn(),
  refresh: vi.fn(),
  auth: { user: null as unknown },
}));

vi.mock("../src/utils/http", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/utils/http")>()),
  http: mocks.http,
}));
vi.mock("../src/utils/users", () => ({ getMe: mocks.getMe }));
vi.mock("../src/utils/useAuth", () => ({
  useAuth: () => ({ user: mocks.auth.user, loading: false, refresh: mocks.refresh, logout: vi.fn() }),
}));

const baseUser: User = {
  id: 3,
  name: "Francisco Melo",
  email: "francisco@example.com",
  role: "user",
  is_verified: true,
  course: "Engenharia Informática",
  institution: null,
  qr_code: null,
};

const withTicket: User = {
  ...baseUser,
  qr_code: "ENEI27.3.ABCDEF",
  ticket: {
    reference: "ENEI-ABC123",
    tier: "geral",
    tier_name: "Passe geral",
    holder_name: "Francisco Melo",
    paid_at: "2026-10-20T10:00:00Z",
  },
};

function renderPage(page: React.ReactElement) {
  return render(<MemoryRouter>{page}</MemoryRouter>);
}

beforeEach(() => {
  mocks.http.mockReset();
  mocks.getMe.mockReset();
  mocks.refresh.mockReset().mockResolvedValue(undefined);
  mocks.auth.user = baseUser;
  mocks.getMe.mockResolvedValue(baseUser);
});
afterEach(cleanup);

describe("perfil: o bilhete vem da API", () => {
  it("mostra a modalidade, o titular e a referência reais, e o QR do bilhete", async () => {
    mocks.getMe.mockResolvedValue(withTicket);
    renderPage(<Profile />);

    expect(await screen.findByRole("heading", { name: "Passe geral" })).toBeInTheDocument();
    expect(screen.getByText("ENEI-ABC123")).toBeInTheDocument();
    expect(screen.getAllByText("Francisco Melo").length).toBeGreaterThan(0);
    expect(screen.queryByText(/experiência completa/i)).toBeNull();
    expect(screen.queryByText(/XXXX/)).toBeNull();
    expect(screen.getByText(/ENEI27\.3\.ABCDEF/)).toBeInTheDocument();
  });

  it("«Ver modalidade» leva às modalidades e «Preparar viagem» às localizações", async () => {
    mocks.getMe.mockResolvedValue(withTicket);
    renderPage(<Profile />);
    await screen.findByRole("heading", { name: "Passe geral" });
    expect(screen.getByRole("link", { name: /ver modalidade/i })).toHaveAttribute("href", "/bilhetes#tipos");
    expect(screen.getByRole("link", { name: /preparar viagem/i })).toHaveAttribute("href", "/informacao-ajuda#localizacoes");
  });

  it("pagamento à espera: usa pending_payment (nada de payment_status) e não mostra QR", async () => {
    mocks.getMe.mockResolvedValue({
      ...baseUser,
      pending_payment: {
        reference: "ENEI-WAIT",
        tier: "geral",
        tier_name: "Passe geral",
        amount_cents: 5000,
        expires_at: "2026-10-20T10:04:00Z",
      },
    });
    renderPage(<Profile />);
    expect(await screen.findByText(/pendente de confirmação/i)).toBeInTheDocument();
    expect(screen.getByText(/ENEI-WAIT/)).toBeInTheDocument();
    expect(screen.queryByText(/código ·/i)).toBeNull();
    expect(screen.queryByText(/ainda não tens uma inscrição/i)).toBeNull();
  });

  it("reembolso a caminho: não diz «ainda não tens uma inscrição»", async () => {
    mocks.getMe.mockResolvedValue({ ...baseUser, refund_due: { reference: "ENEI-REF", amount_cents: 5000 } });
    renderPage(<Profile />);
    expect(await screen.findByText(/vai ser reembolsado/i)).toBeInTheDocument();
    expect(screen.queryByText(/ainda não tens uma inscrição/i)).toBeNull();
  });

  it("sem compra: convida a escolher bilhete", async () => {
    renderPage(<Profile />);
    expect(await screen.findByText(/ainda não tens uma inscrição/i)).toBeInTheDocument();
  });

  it("o estado do email segue a conta (não é fixo) e a página não traz um <main> próprio", async () => {
    mocks.auth.user = { ...baseUser, is_verified: false };
    mocks.getMe.mockResolvedValue({ ...baseUser, is_verified: false });
    const { container } = renderPage(<Profile />);
    await screen.findByText(/ainda não tens uma inscrição/i);
    expect(screen.getAllByText("Email por verificar").length).toBeGreaterThan(0);
    expect(screen.queryByText("Email verificado")).toBeNull();
    expect(container.querySelectorAll("main").length).toBe(0); // o <main> é o do App (#125)
  });
});

describe("segurança: a palavra-passe só se diz atualizada se a API a atualizou", () => {
  const fill = (current = "Antiga-123!", next = "Nova-1234!", confirm = next) => {
    fireEvent.change(screen.getByLabelText(/palavra-passe atual/i), { target: { value: current } });
    fireEvent.change(screen.getByLabelText(/^nova palavra-passe/i), { target: { value: next } });
    fireEvent.change(screen.getByLabelText(/confirmar palavra-passe/i), { target: { value: confirm } });
    fireEvent.click(screen.getByRole("button", { name: /alterar palavra-passe/i }));
  };

  it("chama PUT /auth/password e só depois mostra o sucesso", async () => {
    let resolve: (value: unknown) => void = () => undefined;
    mocks.http.mockReturnValue(new Promise((r) => (resolve = r)));
    renderPage(<Seguranca />);
    fill();

    expect(mocks.http).toHaveBeenCalledWith("/auth/password", {
      method: "PUT",
      body: { current_password: "Antiga-123!", new_password: "Nova-1234!" },
    });
    expect(screen.queryByText(/palavra-passe atualizada/i)).toBeNull();
    resolve({});
    expect(await screen.findByText(/palavra-passe atualizada/i)).toBeInTheDocument();
  });

  it("palavra-passe atual errada: mostra o erro e não diz que atualizou", async () => {
    mocks.http.mockRejectedValue(new ApiError(401, "Current password is incorrect"));
    renderPage(<Seguranca />);
    fill();
    expect(await screen.findByRole("alert")).toHaveTextContent("A palavra-passe atual está incorreta.");
    expect(screen.queryByText(/palavra-passe atualizada/i)).toBeNull();
  });

  it("não deixa enviar se não cumpre as regras ou não coincide (sem pedido)", async () => {
    renderPage(<Seguranca />);
    fill("Antiga-123!", "curta");
    expect(await screen.findByRole("alert")).toHaveTextContent(/requisitos/i);
    fill("Antiga-123!", "Nova-1234!", "Outra-1234!");
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/não coincidem/i));
    expect(mocks.http).not.toHaveBeenCalled();
  });

  it("as regras da nova palavra-passe verificam-se ao vivo", () => {
    renderPage(<Seguranca />);
    const rules = () => screen.getAllByRole("listitem").filter((li) => li.hasAttribute("data-ok"));
    expect(rules()).toHaveLength(4);
    expect(rules().every((li) => li.getAttribute("data-ok") === "false")).toBe(true);

    fireEvent.change(screen.getByLabelText(/^nova palavra-passe/i), { target: { value: "abcdefgh" } });
    expect(rules().map((li) => li.getAttribute("data-ok"))).toEqual(["true", "false", "false", "false"]);

    fireEvent.change(screen.getByLabelText(/^nova palavra-passe/i), { target: { value: "Abcdefg1!" } });
    expect(rules().every((li) => li.getAttribute("data-ok") === "true")).toBe(true);
  });

  it("não tem o botão de apagar a conta (o backend ainda não o tem)", () => {
    renderPage(<Seguranca />);
    expect(screen.queryByText(/apagar/i)).toBeNull();
    expect(screen.queryByText(/eliminar/i)).toBeNull();
  });
});

describe("dados pessoais: só o nome se guarda, e pela API", () => {
  it("envia só o nome a PUT /users/me, atualiza a conta e só depois diz que guardou", async () => {
    mocks.http.mockResolvedValue({});
    renderPage(<DadosPessoais />);
    fireEvent.change(screen.getByLabelText(/nome completo/i), { target: { value: "  Francisco M. Melo " } });
    fireEvent.click(screen.getByRole("button", { name: /guardar alterações/i }));

    expect(await screen.findByText("Dados atualizados.")).toBeInTheDocument();
    expect(mocks.http).toHaveBeenCalledWith("/users/me", { method: "PUT", body: { name: "Francisco M. Melo" } });
    expect(mocks.refresh).toHaveBeenCalledTimes(1);
  });

  it("o email, a instituição e o curso só se mostram (não se fingem editáveis)", () => {
    renderPage(<DadosPessoais />);
    expect(screen.getByLabelText(/^email/i)).toHaveAttribute("readonly");
    expect(screen.getByLabelText(/instituição/i)).toHaveAttribute("readonly");
    expect(screen.getByLabelText(/curso/i)).toHaveAttribute("readonly");
  });

  it("se a API recusa, mostra o erro e não diz que guardou", async () => {
    mocks.http.mockRejectedValue(new ApiError(500, "x"));
    renderPage(<DadosPessoais />);
    fireEvent.click(screen.getByRole("button", { name: /guardar alterações/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/não foi possível guardar/i);
    expect(screen.queryByText("Dados atualizados.")).toBeNull();
    expect(mocks.refresh).not.toHaveBeenCalled();
  });
});
