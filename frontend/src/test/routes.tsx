// Monta a aplicação inteira (Navbar, rotas, Footer) num MemoryRouter, com a API simulada.
// Usado pelos testes que percorrem todas as rotas.
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, vi } from "vitest";
import { AppShell } from "../App";
import appSource from "../App.tsx?raw";

export const USER = {
  id: 3,
  name: "Francisco Melo",
  email: "francisco@example.com",
  role: "user",
  is_verified: true,
  course: "Engenharia Informática",
  institution: null,
  qr_code: null,
  ticket: null,
  pending_payment: null,
  refund_due: null,
  student_verification_status: "verified",
};

const TIERS = [
  { tier: "geral", name: "Passe geral", price_cents: 2500, currency: "EUR", is_student: false, sale_open: true, available: true },
];

/** Exemplos para os caminhos com parâmetros que precisam deles para mostrar a página. */
const QUERY: Record<string, string> = {
  "/bilhetes/checkout/aguardar": "?ref=ENEI-ABC123",
  "/bilhetes/checkout/sucesso": "?ref=ENEI-ABC123",
  "/bilhetes/checkout/erro": "?ref=ENEI-ABC123",
  "/conta/verificar": "?token=abc",
  "/conta/redefinir": "?token=abc",
};

/** Os caminhos declarados em App.tsx, mais um que não existe (a página 404). */
export function allRoutes(): string[] {
  const paths = [...appSource.matchAll(/path="([^"]+)"/g)].map((m) => m[1]).filter((p) => p !== "*");
  return [...new Set(paths), "/esta-pagina-nao-existe"];
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

/** Simula a API: com `loggedIn` há sessão; sem ela, `/auth/me` responde 401. */
export function stubApi({ loggedIn }: { loggedIn: boolean }) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.endsWith("/auth/me") || url.endsWith("/users/me")) {
      return loggedIn ? json(200, USER) : json(401, { detail: "Not authenticated. Missing access token cookie." });
    }
    if (url.endsWith("/payment/tiers")) return json(200, TIERS);
    if (url.includes("/payment/transactions/")) {
      return json(200, {
        reference: "ENEI-ABC123", ticket_tier: "geral", status: "pending", amount_cents: 2500, quantity: 1,
        currency: "EUR", phone: "912345678", expires_at: new Date(Date.now() + 600_000).toISOString(),
        confirmed_at: null, created_at: new Date().toISOString(),
      });
    }
    return json(200, {});
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("reduce"),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
  }));
  return fetchMock;
}

export const isProtected = (path: string) =>
  path === "/perfil" || ["/conta/alterar-palavra-passe", "/conta/perfil", "/conta/dados", "/conta/seguranca"].includes(path);

/** Abre `path` com a API simulada e espera que a página deixe de carregar. */
export async function renderRoute(path: string) {
  stubApi({ loggedIn: isProtected(path) });
  const view = render(
    <MemoryRouter initialEntries={[path + (QUERY[path] ?? "")]}>
      <AppShell />
    </MemoryRouter>,
  );
  await waitFor(() => expect(screen.queryByText(/a carregar/i)).toBeNull());
  return view;
}
