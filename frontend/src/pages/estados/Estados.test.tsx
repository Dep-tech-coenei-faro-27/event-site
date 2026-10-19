import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LinkExpired from "./LinkExpired";
import SessionEnded from "./SessionEnded";
import TooManyAttempts from "./TooManyAttempts";
import UnverifiedAccount from "./UnverifiedAccount";

const mocks = vi.hoisted(() => ({ http: vi.fn() }));
vi.mock("../../utils/http", () => ({ http: mocks.http }));

function Where() {
  return <div data-testid="where">{useLocation().pathname}</div>;
}

const renderPage = (element: React.ReactElement, entry: string | { pathname: string; state?: unknown } = "/x") =>
  render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/x" element={element} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  mocks.http.mockReset();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  document.body.removeAttribute("data-page");
  document.body.className = "";
});

describe("estados da conta", () => {
  it("sessão terminada: leva a entrar outra vez e marca a página", () => {
    renderPage(<SessionEnded />);
    expect(screen.getByRole("heading", { name: /a tua sessão terminou/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /iniciar sessão novamente/i })).toHaveAttribute("href", "/conta");
    expect(document.body.dataset.page).toBe("estado");
    expect(document.body).toHaveClass("system-state-page");
  });

  it("ligação expirada: pede uma nova e volta ao início de sessão", () => {
    renderPage(<LinkExpired />);
    expect(screen.getByRole("link", { name: /pedir nova ligação/i })).toHaveAttribute("href", "/conta/recuperar");
    expect(screen.getByRole("link", { name: /voltar ao início de sessão/i })).toHaveAttribute("href", "/conta");
    expect(document.body).toHaveClass("system-state-page--warning");
  });

  it("conta por verificar: mostra o email e reenvia a ligação", async () => {
    mocks.http.mockResolvedValue(null);
    renderPage(<UnverifiedAccount />, { pathname: "/x", state: { email: "ana@example.com" } });
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /reenviar email/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /email reenviado/i })).toBeDisabled());
    expect(mocks.http).toHaveBeenCalledWith("/auth/resend-verification-email", { method: "POST", body: { email: "ana@example.com" } });
  });

  it("conta por verificar: se o reenvio falha, diz-o e deixa tentar mais tarde", async () => {
    mocks.http.mockImplementation(async () => {
      throw new Error("x");
    });
    renderPage(<UnverifiedAccount />, "/x?email=ana@example.com");
    fireEvent.click(screen.getByRole("button", { name: /reenviar email/i }));
    expect(await screen.findByText(/não foi possível reenviar agora/i)).toBeInTheDocument();
  });

  it("conta por verificar sem email conhecido: não oferece reenviar, só corrigir o endereço", () => {
    renderPage(<UnverifiedAccount />);
    expect(screen.queryByRole("button", { name: /reenviar email/i })).toBeNull();
    expect(screen.getByRole("link", { name: /corrigir endereço/i })).toHaveAttribute("href", "/conta/criar");
  });
});

describe("demasiadas tentativas", () => {
  it("conta o tempo do servidor e só depois deixa tentar outra vez", () => {
    vi.useFakeTimers();
    renderPage(<TooManyAttempts />, { pathname: "/x", state: { retryAfterSeconds: 3 } });
    const retry = screen.getByRole("button", { name: /aguardar para tentar/i });
    expect(retry).toBeDisabled();
    expect(screen.getByText("00:03")).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(1000));
    act(() => void vi.advanceTimersByTime(1000));
    expect(screen.getByText("00:01")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /aguardar para tentar/i })).toBeDisabled();
    act(() => void vi.advanceTimersByTime(1000));
    const ready = screen.getByRole("button", { name: /tentar novamente/i });
    expect(ready).toBeEnabled();
    expect(screen.getByText(/já podes voltar a tentar/i)).toBeInTheDocument();
    fireEvent.click(ready);
    expect(screen.getByTestId("where")).toHaveTextContent("/conta");
  });

  it("sem o tempo do servidor assume 15 minutos", () => {
    renderPage(<TooManyAttempts />);
    expect(screen.getByText("15:00")).toBeInTheDocument();
  });
});
