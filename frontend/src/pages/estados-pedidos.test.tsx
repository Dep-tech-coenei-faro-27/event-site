// Matriz página × estado de cada ecrã que lê da API: a carregar, sucesso, vazio, erro de rede, 5xx,
// 401 e 429. Cada célula prova o estado certo e a ausência do estado errado (por exemplo, uma falha
// nunca é «sem inscrição» nem leva ao login). O `fetch` é simulado; o cliente HTTP é o verdadeiro.
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ProtectedRoute from "../components/ProtectedRoute";
import { AuthProvider } from "../utils/AuthContext";
import { useAuth } from "../utils/useAuth";
import { AuthContext, type AuthContextValue, type User } from "../utils/authContextValue";
import Checkout from "./checkout/Checkout";
import CheckoutSuccess from "./checkout/CheckoutSuccess";
import CheckoutWaiting from "./checkout/CheckoutWaiting";
import ProfilePage from "./Profile";

// ---------- API simulada ----------

type Reply = "pending" | "network" | (() => Response);

const json = (status: number, body: unknown, headers: Record<string, string> = {}) => () =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });

const NO_SESSION = json(401, { detail: "Not authenticated. Missing access token cookie." });

/** As falhas que não dizem nada sobre os dados: o ecrã mostra o erro e «Tentar novamente». */
const FAILURES: [string, Reply, RegExp][] = [
  ["erro de rede", "network", /não conseguimos ligar ao servidor/i],
  ["5xx", json(503, { detail: "Service Unavailable" }), /o servidor não conseguiu responder/i],
  ["429", json(429, { detail: "Too many requests" }, { "Retry-After": "30" }), /demasiados pedidos\. tenta novamente dentro de 30 segundos/i],
];

let routes: Record<string, Reply[]>;
let signals: AbortSignal[];

/** Cada caminho responde pela ordem da lista; a última resposta repete-se. */
function stubApi(map: Record<string, Reply | Reply[]>) {
  routes = Object.fromEntries(Object.entries(map).map(([k, v]) => [k, Array.isArray(v) ? [...v] : [v]]));
  signals = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.signal) signals.push(init.signal);
      const key = Object.keys(routes).find((path) => url.endsWith(path) || url.includes(`${path}/`));
      if (!key) return Promise.resolve(json(200, {})());
      const list = routes[key];
      const reply = list.length > 1 ? list.shift()! : list[0];
      if (reply === "pending") {
        return new Promise<Response>((_, reject) =>
          init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError"))),
        );
      }
      if (reply === "network") return Promise.reject(new TypeError("Failed to fetch"));
      return Promise.resolve(reply());
    }),
  );
}

// ---------- dados ----------

const BASE_USER: User = {
  id: 3, name: "Francisco Melo", email: "francisco@example.com", role: "user", is_verified: true,
  qr_code: null, ticket: null, pending_payment: null, refund_due: null,
};
const TICKET = { reference: "ENEI-OK1", tier: "geral", tier_name: "Passe geral", holder_name: "Francisco Melo", paid_at: null };
const WITH_TICKET = { ...BASE_USER, qr_code: "QR-123", ticket: TICKET };
const PENDING = {
  ...BASE_USER,
  pending_payment: { reference: "ENEI-RETOMA", tier: "geral", tier_name: "Passe geral", amount_cents: 2500, expires_at: new Date(Date.now() + 600_000).toISOString() },
};
const TIERS = [{ tier: "geral", name: "Passe geral", price_cents: 2500, currency: "EUR", is_student: false, sale_open: true, available: true }];
const TRANSACTION = {
  reference: "ENEI-RETOMA", ticket_tier: "geral", status: "pending", amount_cents: 2500, quantity: 1, currency: "EUR",
  phone: "912345678", expires_at: new Date(Date.now() + 600_000).toISOString(), confirmed_at: null, created_at: new Date().toISOString(),
};

// ---------- montagem ----------

function Where() {
  const { pathname, search } = useLocation();
  return <div data-testid="where">{pathname + search}</div>;
}

const auth = (user: User | null, extra: Partial<AuthContextValue> = {}): AuthContextValue => ({
  user, loading: false, error: null, refresh: vi.fn(), retry: vi.fn(), logout: vi.fn(), ...extra,
});

function mount(path: string, element: ReactNode, value: AuthContextValue | "real" = auth(BASE_USER)) {
  const tree = (
    <Routes>
      <Route path={path} element={element} />
      <Route path="*" element={<Where />} />
    </Routes>
  );
  return render(
    <MemoryRouter initialEntries={[path]}>
      {value === "real" ? <AuthProvider>{tree}</AuthProvider> : <AuthContext.Provider value={value}>{tree}</AuthContext.Provider>}
    </MemoryRouter>,
  );
}

const where = () => screen.queryByTestId("where")?.textContent ?? null;

/** O erro aparece com a mensagem certa, «Tentar novamente» e o foco. */
async function expectFailure(message: RegExp) {
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(message);
  expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  expect(document.activeElement).toBe(alert);
  return alert;
}

const retry = () => fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));

/** O pedido cancela-se ao desmontar e o React não avisa de nada. */
async function expectCleanUnmount(view: ReturnType<typeof render>) {
  const consoleError = vi.spyOn(console, "error");
  await waitFor(() => expect(signals.length).toBeGreaterThan(0));
  view.unmount();
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  expect(signals.every((signal) => signal.aborted)).toBe(true);
  expect(consoleError).not.toHaveBeenCalled();
}

beforeEach(() => {
  sessionStorage.clear();
  document.body.removeAttribute("data-page");
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------- sessão (AuthContext + ProtectedRoute) ----------

describe("sessão: AuthContext e ProtectedRoute", () => {
  const open = () =>
    render(
      <MemoryRouter initialEntries={["/perfil"]}>
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/perfil" element={<p>área privada</p>} />
            </Route>
            <Route path="*" element={<Where />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

  it("a carregar: «A carregar…» anunciado, sem ir ao login nem mostrar a área privada", () => {
    stubApi({ "/auth/me": "pending" });
    open();
    expect(screen.getByRole("status")).toHaveTextContent(/a carregar/i);
    expect(where()).toBeNull();
    expect(screen.queryByText("área privada")).toBeNull();
  });

  it("sucesso: mostra a área privada", async () => {
    stubApi({ "/auth/me": json(200, BASE_USER) });
    open();
    expect(await screen.findByText("área privada")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("401 (sem sessão): vai ao login, sem mostrar erro", async () => {
    stubApi({ "/auth/me": NO_SESSION });
    open();
    await waitFor(() => expect(where()).toBe("/conta"));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it.each(FAILURES)("%s: mostra o erro com «Tentar novamente» e não vai ao login", async (_name, reply, message) => {
    stubApi({ "/auth/me": reply });
    open();
    await expectFailure(message);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/não foi possível confirmar a tua sessão/i);
    expect(where()).toBeNull();
    expect(screen.queryByText("área privada")).toBeNull();
  });

  it("«Tentar novamente» volta a «a carregar» e, com a API de volta, abre a área privada", async () => {
    stubApi({ "/auth/me": ["network", json(200, BASE_USER)] });
    open();
    await expectFailure(/não conseguimos ligar/i);
    retry();
    expect(screen.getByRole("status")).toHaveTextContent(/a carregar/i);
    expect(await screen.findByText("área privada")).toBeInTheDocument();
    expect(where()).toBeNull();
  });

  it("refresh com falha de rede mantém o utilizador (não expulsa a meio de uma página privada)", async () => {
    stubApi({ "/auth/me": [json(200, BASE_USER), "network"] });
    function Grab() {
      const { refresh } = useAuth();
      return (
        <>
          <p>área privada</p>
          <button type="button" onClick={() => void refresh()}>
            Atualizar
          </button>
        </>
      );
    }
    render(
      <MemoryRouter initialEntries={["/perfil"]}>
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/perfil" element={<Grab />} />
            </Route>
            <Route path="*" element={<Where />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("área privada")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Atualizar" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(screen.getByText("área privada")).toBeInTheDocument();
    expect(where()).toBeNull();
  });

  it("cancela a verificação da sessão ao desmontar, sem avisos do React", async () => {
    stubApi({ "/auth/me": "pending" });
    await expectCleanUnmount(open());
  });
});

// ---------- Profile ----------

describe("Profile (/users/me)", () => {
  const open = () => mount("/perfil", <ProfilePage />);
  const NO_REGISTRATION = /ainda não tens uma inscrição/i;

  it("a carregar: «A carregar…», nunca «Ainda não tens uma inscrição»", () => {
    stubApi({ "/users/me": "pending" });
    open();
    expect(screen.getByRole("status")).toHaveTextContent(/a carregar/i);
    expect(screen.queryByText(NO_REGISTRATION)).toBeNull();
    expect(screen.queryByText(/bilhete confirmado/i)).toBeNull();
  });

  it("sucesso com bilhete: mostra a modalidade e a referência", async () => {
    stubApi({ "/users/me": json(200, WITH_TICKET) });
    open();
    expect(await screen.findByText("ENEI-OK1")).toBeInTheDocument();
    expect(screen.queryByText(NO_REGISTRATION)).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("vazio (sem bilhete nem pagamento): «Ainda não tens uma inscrição»", async () => {
    stubApi({ "/users/me": json(200, BASE_USER) });
    open();
    expect(await screen.findByText(NO_REGISTRATION)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it.each(FAILURES)("%s: erro com «Tentar novamente», nunca «Ainda não tens uma inscrição»", async (_name, reply, message) => {
    stubApi({ "/users/me": reply });
    open();
    await expectFailure(message);
    expect(screen.queryByText(NO_REGISTRATION)).toBeNull();
    expect(where()).toBeNull();
  });

  it("401: sessão terminada, vai ao login sem mostrar erro nem «sem inscrição»", async () => {
    stubApi({ "/users/me": NO_SESSION });
    open();
    await waitFor(() => expect(where()).toBe("/conta?sessao=terminada"));
    expect(screen.queryByText(NO_REGISTRATION)).toBeNull();
  });

  it("«Tentar novamente» pede outra vez e mostra o bilhete", async () => {
    stubApi({ "/users/me": [json(503, {}), json(200, WITH_TICKET)] });
    open();
    await expectFailure(/o servidor não conseguiu responder/i);
    retry();
    expect(await screen.findByText("ENEI-OK1")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("cancela o pedido ao desmontar, sem avisos do React", async () => {
    stubApi({ "/users/me": "pending" });
    await expectCleanUnmount(open());
  });
});

// ---------- CheckoutSuccess ----------

describe("CheckoutSuccess (/users/me)", () => {
  const PATH = "/bilhetes/checkout/sucesso";
  const open = () => mount(PATH, <CheckoutSuccess />);
  const SUCCESS = /o teu lugar está garantido/i;

  it("a carregar: «A carregar…», sem dar o lugar por garantido nem redirecionar", () => {
    stubApi({ "/users/me": "pending" });
    open();
    expect(screen.getByRole("status")).toHaveTextContent(/a carregar/i);
    expect(screen.queryByText(SUCCESS)).toBeNull();
    expect(where()).toBeNull();
  });

  it("sucesso: mostra o bilhete", async () => {
    stubApi({ "/users/me": json(200, WITH_TICKET) });
    open();
    expect(await screen.findByRole("heading", { name: SUCCESS })).toBeInTheDocument();
    expect(screen.getByText("ENEI-OK1")).toBeInTheDocument();
  });

  it("vazio (sem bilhete): volta aos bilhetes", async () => {
    stubApi({ "/users/me": json(200, BASE_USER) });
    open();
    await waitFor(() => expect(where()).toBe("/bilhetes"));
  });

  it.each(FAILURES)("%s: erro com «Tentar novamente», sem redirecionar nem dizer que não há bilhete", async (_name, reply, message) => {
    stubApi({ "/users/me": reply });
    open();
    await expectFailure(message);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/não conseguimos confirmar o teu bilhete/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/o bilhete não se perde/i);
    expect(where()).toBeNull();
    expect(screen.queryByText(SUCCESS)).toBeNull();
  });

  it("401: vai ao login (e volta aqui depois)", async () => {
    stubApi({ "/users/me": NO_SESSION });
    open();
    await waitFor(() => expect(where()).toBe("/conta"));
  });

  it("«Tentar novamente» pede outra vez e mostra o bilhete", async () => {
    stubApi({ "/users/me": ["network", json(200, WITH_TICKET)] });
    open();
    await expectFailure(/não conseguimos ligar/i);
    retry();
    expect(await screen.findByRole("heading", { name: SUCCESS })).toBeInTheDocument();
  });

  it("cancela o pedido ao desmontar, sem avisos do React", async () => {
    stubApi({ "/users/me": "pending" });
    await expectCleanUnmount(open());
  });
});

// ---------- CheckoutWaiting sem referência guardada ----------

describe("CheckoutWaiting a retomar pela conta (/users/me)", () => {
  const PATH = "/bilhetes/checkout/aguardar";
  const open = () => mount(PATH, <CheckoutWaiting />);
  const WAITING = /confirma no mb way/i;

  it("a carregar: «A carregar…», sem pedir para confirmar no MB WAY nem redirecionar", () => {
    stubApi({ "/users/me": "pending" });
    open();
    expect(screen.getByRole("status")).toHaveTextContent(/a carregar/i);
    expect(screen.queryByText(WAITING)).toBeNull();
    expect(where()).toBeNull();
  });

  it("sucesso (pagamento à espera): segue esse pagamento", async () => {
    stubApi({ "/users/me": json(200, PENDING), "/payment/transactions": json(200, TRANSACTION) });
    open();
    expect(await screen.findByRole("heading", { name: WAITING })).toBeInTheDocument();
    expect(screen.getByText("ENEI-RETOMA")).toBeInTheDocument();
  });

  it("vazio (nenhum pagamento à espera): volta ao checkout", async () => {
    stubApi({ "/users/me": json(200, BASE_USER) });
    open();
    await waitFor(() => expect(where()).toBe("/bilhetes/checkout"));
  });

  it.each(FAILURES)("%s: erro com «Tentar novamente», sem redirecionar nem dizer que não há pagamento", async (_name, reply, message) => {
    stubApi({ "/users/me": reply });
    open();
    await expectFailure(message);
    expect(screen.getByRole("alert")).toHaveTextContent(/o pagamento não se perde/i);
    expect(where()).toBeNull();
    expect(screen.queryByText(WAITING)).toBeNull();
  });

  it("401: vai ao login (e volta aqui depois)", async () => {
    stubApi({ "/users/me": NO_SESSION });
    open();
    await waitFor(() => expect(where()).toBe("/conta"));
  });

  it("«Tentar novamente» pede outra vez e retoma o pagamento", async () => {
    stubApi({ "/users/me": [json(500, {}), json(200, PENDING)], "/payment/transactions": json(200, TRANSACTION) });
    open();
    await expectFailure(/o servidor não conseguiu responder/i);
    retry();
    expect(await screen.findByText("ENEI-RETOMA")).toBeInTheDocument();
  });

  it("cancela o pedido ao desmontar, sem avisos do React", async () => {
    stubApi({ "/users/me": "pending" });
    await expectCleanUnmount(open());
  });
});

// ---------- Checkout (modalidades e conta) ----------

describe("Checkout (/payment/tiers e /users/me)", () => {
  const PATH = "/bilhetes/checkout";
  const open = (value?: AuthContextValue) => mount(PATH, <Checkout />, value);

  it("sessão por confirmar (rede, 5xx, 429): erro com «Tentar novamente», sem o convite para entrar", async () => {
    const retrySession = vi.fn();
    stubApi({});
    open(auth(null, { error: new TypeError("x"), retry: retrySession }));
    await screen.findByRole("alert");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/não foi possível confirmar a tua sessão/i);
    expect(screen.queryByRole("link", { name: /entrar|criar conta/i })).toBeNull();
    retry();
    expect(retrySession).toHaveBeenCalledOnce();
  });

  it("a carregar: «A carregar…» anunciado, sem o formulário", () => {
    stubApi({ "/payment/tiers": "pending", "/users/me": "pending" });
    open();
    expect(screen.getByRole("status")).toHaveTextContent(/a carregar/i);
    expect(screen.queryByRole("radio")).toBeNull();
  });

  it("sucesso: mostra as modalidades", async () => {
    stubApi({ "/payment/tiers": json(200, TIERS), "/users/me": json(200, BASE_USER) });
    open();
    expect(await screen.findByRole("radio", { name: /passe geral/i })).toBeInTheDocument();
  });

  it.each(FAILURES)("%s: erro com «Tentar novamente» em vez de «recarrega a página»", async (_name, reply, message) => {
    stubApi({ "/payment/tiers": reply, "/users/me": json(200, BASE_USER) });
    open();
    await expectFailure(message);
    expect(screen.queryByText(/recarrega a página/i)).toBeNull();
    expect(screen.queryByRole("radio")).toBeNull();
  });

  it("«Tentar novamente» pede outra vez e mostra as modalidades", async () => {
    stubApi({ "/payment/tiers": ["network", json(200, TIERS)], "/users/me": json(200, BASE_USER) });
    open();
    await expectFailure(/não conseguimos ligar/i);
    retry();
    expect(await screen.findByRole("radio", { name: /passe geral/i })).toBeInTheDocument();
  });

  it("cancela os pedidos ao desmontar, sem avisos do React", async () => {
    stubApi({ "/payment/tiers": "pending", "/users/me": "pending" });
    await expectCleanUnmount(open());
  });
});
