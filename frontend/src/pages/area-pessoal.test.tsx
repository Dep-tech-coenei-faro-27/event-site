/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import AccountLayout from "../components/dashboard/AccountLayout";
import authLayoutSource from "../components/auth/AuthLayout.tsx?raw";
import ScrollToTop from "../components/ScrollToTop";
import { renderRoute } from "../test/routes";

// O CSS não se importa com `?raw` nos testes (o vitest devolve-o vazio): lê-se do disco.
const css = (name: string) => readFileSync(join(import.meta.dirname, "..", name), "utf8");
const contaOverrides = css("conta.overrides.css");

const logout = vi.fn();
vi.mock("../utils/useAuth", () => ({
  useAuth: () => ({
    user: { name: "Francisco Melo", email: "francisco@example.com", is_verified: true },
    loading: false,
    refresh: vi.fn(),
    logout,
  }),
}));

afterEach(() => {
  cleanup();
  logout.mockClear();
  vi.unstubAllGlobals();
});

const at = (element: React.ReactElement, path = "/") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <main>{element}</main>
    </MemoryRouter>,
  );

describe("telemóvel", () => {
  it("«Sair» está na barra lateral em ecrã largo e, no telemóvel, no fundo da página (fora da barra que desliza)", () => {
    at(
      <AccountLayout metaTitle="Dados" metaDescription="d" eyebrow="CONTA" title="Dados" lead="l">
        <p>conteúdo</p>
      </AccountLayout>,
    );
    // O jsdom não aplica o CSS: há dois botões no DOM, cada um escondido num dos tamanhos.
    const buttons = screen.getAllByRole("button", { name: "Sair" });
    expect(buttons).toHaveLength(2);
    buttons.forEach((b) => expect(b.closest("nav")).toBeNull());
    const [sidebar, bottom] = buttons;
    expect(sidebar.parentElement!.className).toContain("max-[900px]:hidden");
    expect(bottom.parentElement!.className).toContain("min-[901px]:hidden");
    const content = screen.getByText("conteúdo");
    expect(content.compareDocumentPosition(bottom) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    fireEvent.click(bottom);
    expect(logout).toHaveBeenCalledTimes(1);
  });

  it("a apresentação das páginas de entrada encolhe até 900 px para o formulário aparecer logo", () => {
    expect(authLayoutSource).toContain('import "../../conta.overrides.css"');
    expect(contaOverrides).toMatch(/@media \(max-width: 900px\)[\s\S]*\.auth-points\s*\{\s*display: none;/);
    expect(contaOverrides).toMatch(/\.auth-aside\s*\{[^}]*min-height: 0;/);
  });
});

describe("separadores da área pessoal", () => {
  it("mudar de separador troca só o conteúdo: a moldura (barra lateral e «Sair») é a mesma e o título muda", async () => {
    await renderRoute("/conta/dados");
    const nav = screen.getByRole("navigation", { name: "Área pessoal" });
    const heading = () => screen.getByRole("heading", { level: 1 }).textContent;
    expect(heading()).toMatch(/dados/i);

    fireEvent.click(within(nav).getByRole("link", { name: "Segurança" }));
    await screen.findByRole("heading", { level: 1, name: /seguran/i });
    expect(screen.getByRole("navigation", { name: "Área pessoal" })).toBe(nav); // o mesmo elemento, não remontado
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);

    fireEvent.click(within(nav).getByRole("link", { name: "Visão geral" }));
    await screen.findByRole("heading", { level: 1, name: /olá/i });
    expect(screen.getByRole("navigation", { name: "Área pessoal" })).toBe(nav);
  });

  it("ao mudar para a Visão geral não aparece «a carregar»: os dados já estavam carregados pela moldura", async () => {
    await renderRoute("/conta/dados");
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30)); // deixa a moldura acabar o pedido de /users/me
    });
    const nav = screen.getByRole("navigation", { name: "Área pessoal" });
    fireEvent.click(within(nav).getByRole("link", { name: "Visão geral" }));
    // logo a seguir ao clique, antes de qualquer pedido novo, já se vê a página sem estado de carregamento
    expect(screen.getByRole("heading", { level: 1, name: /olá/i })).toBeInTheDocument();
    expect(screen.queryByText(/a carregar/i)).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("não volta ao topo ao mudar de separador, mas volta ao mudar de página", () => {
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    function Go() {
      const navigate = useNavigate();
      return (
        <>
          <button onClick={() => navigate("/conta/seguranca")}>separador</button>
          <button onClick={() => navigate("/sobre")}>página</button>
        </>
      );
    }
    render(
      <MemoryRouter initialEntries={["/conta/dados"]}>
        <ScrollToTop />
        <Go />
      </MemoryRouter>,
    );
    expect(scrollTo).toHaveBeenCalledTimes(1); // primeira entrada
    scrollTo.mockClear();
    fireEvent.click(screen.getByText("separador"));
    expect(scrollTo).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("página"));
    expect(scrollTo).toHaveBeenCalledTimes(1);
  });
});

describe("Dados pessoais sem Instituição nem Curso", () => {
  it("só mostram o nome (editável) e o email", async () => {
    await renderRoute("/conta/dados");
    expect(screen.queryByLabelText("Instituição")).toBeNull();
    expect(screen.queryByLabelText("Curso")).toBeNull();
    expect(screen.getByLabelText("Nome completo")).toBeInTheDocument();
  });
});

/** Os pedidos feitos ao `fetch` simulado que o `renderRoute` instalou. */
const fetchCalls = () => (globalThis.fetch as unknown as { mock: { calls: [string, RequestInit?][] } }).mock.calls;
const putBody = () => {
  const put = fetchCalls().find(([, init]) => init?.method === "PUT");
  return put ? JSON.parse(put[1]!.body as string) : undefined;
};

describe("Dados pessoais: contacto", () => {
  it("tem o campo «Contacto» (opcional), antes do email, que se guarda normalizado junto com o nome", async () => {
    await renderRoute("/conta/dados");
    const field = screen.getByLabelText("Contacto") as HTMLInputElement;
    expect(field).toHaveAttribute("type", "tel");
    expect(field).not.toBeRequired();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();

    fireEvent.change(field, { target: { value: "+351 912-345.678" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar alterações/i }));
    await screen.findByText("Dados atualizados.");

    expect(putBody()).toEqual({ name: "Francisco Melo", phone: "+351912345678" });
    expect(field.value).toBe("+351912345678");
  });

  it("um número inválido não se envia e mostra a razão junto ao campo", async () => {
    await renderRoute("/conta/dados");
    fireEvent.change(screen.getByLabelText("Contacto"), { target: { value: "12345" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar alterações/i }));

    expect(await screen.findByText(/9 a 15 dígitos/)).toBeInTheDocument();
    expect(screen.getByLabelText("Contacto")).toHaveAttribute("aria-invalid", "true");
    expect(putBody()).toBeUndefined();
  });

  it("apagar o número guarda «sem contacto» (null)", async () => {
    await renderRoute("/conta/dados");
    fireEvent.change(screen.getByLabelText("Contacto"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /guardar alterações/i }));
    await screen.findByText("Dados atualizados.");

    expect(putBody()).toEqual({ name: "Francisco Melo", phone: null });
  });
});
