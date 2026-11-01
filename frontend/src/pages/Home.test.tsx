import { cleanup, render, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useMotion } from "../utils/useMotion";
import Home from "./Home";

function Layer() {
  useMotion();
  return null;
}

function renderHome() {
  return render(
    <MemoryRouter>
      <main>
        <Home />
      </main>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// O jsdom não tem matchMedia; o hook de animações precisa dele.
const stubMatchMedia = () => vi.stubGlobal("matchMedia", () => ({ matches: false }));

describe("página inicial", () => {
  it("mantém cinco secções com informação direta", () => {
    const { container } = renderHome();
    const main = container.querySelector("main")!;
    const sections = [...main.children].filter((el) => el.tagName === "SECTION");
    expect(sections).toHaveLength(5);
    expect(sections[0]).toHaveClass("hero-home");
    expect(sections.slice(1).every((s) => s.classList.contains("section"))).toBe(true);
  });

  it("cada ligação vai para a página certa (nenhuma é âncora solta nem `#`)", () => {
    const { container } = renderHome();
    const main = container.querySelector("main")!;
    const links = within(main).getAllByRole("link");
    const hrefOf = (name: string | RegExp, nth = 0) =>
      within(main).getAllByRole("link", { name })[nth].getAttribute("href");

    expect(hrefOf("Saber mais")).toBe("/sobre");
    expect(hrefOf("Ver programa completo")).toBe("/agenda");
    expect(hrefOf("Ver locais e acessos")).toBe("/informacao-ajuda#localizacoes");
    expect(hrefOf("Tenho dúvidas")).toBe("/informacao-ajuda");
    const buy = within(main).getAllByRole("link", { name: /Comprar bilhete/i });
    expect(buy).toHaveLength(2);
    buy.forEach((a) => expect(a).toHaveAttribute("href", "/bilhetes"));

    links.forEach((a) => {
      const href = a.getAttribute("href");
      expect(href, a.textContent ?? "").toBeTruthy();
      expect(href!.startsWith("#")).toBe(false);
    });
  });

  it("não há botões a fingir de ligação nem botões dentro de ligações (HTML inválido)", () => {
    const { container } = renderHome();
    expect(container.querySelectorAll("a button")).toHaveLength(0);
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  it("os botões do desenho novo usam a classe .btn", () => {
    const { container } = renderHome();
    const buttons = [...container.querySelectorAll("a.btn")];
    expect(buttons).toHaveLength(6);
    buttons.forEach((b) => expect(b.className).toMatch(/btn--(primary|secondary|dark|outline-light)/));
  });

  it("marca o body com data-page=inicio e limpa ao sair (o CSS da página depende disto)", () => {
    const { unmount } = renderHome();
    expect(document.body.dataset.page).toBe("inicio");
    unmount();
    expect(document.body.dataset.page).toBeUndefined();
  });

  it("define o título da página", () => {
    renderHome();
    expect(document.title).toBe("ENEI 2027");
  });

  it("o cartão mostra data, local e duração", () => {
    const { container } = renderHome();
    const card = container.querySelector(".stats-overlap")!;
    ["DATA", "LOCAL", "BILHETES"].forEach((label) =>
      expect(within(card as HTMLElement).getByText(label)).toBeInTheDocument(),
    );
  });

  it("todas as secções (menos o hero, que anima ao carregar) têm elementos que se revelam com o scroll", () => {
    stubMatchMedia();
    const { container } = render(
      <MemoryRouter>
        <main>
          <Layer />
          <Home />
        </main>
      </MemoryRouter>,
    );
    const sections = [...container.querySelectorAll("main > section")].slice(1);
    expect(sections).toHaveLength(4);
    sections.forEach((section) => {
      const name = section.className;
      expect(section.querySelectorAll("[data-motion-item]").length, name).toBeGreaterThan(0);
    });
  });

  it("mostra três imagens provisórias e a fotografia do campus com crédito à UAlg", () => {
    const { container } = renderHome();
    const photos = container.querySelectorAll(".preview-photo");
    expect(photos).toHaveLength(4);
    Array.from(photos).slice(0,3).forEach(photo => {
      expect(within(photo as HTMLElement).getByRole("img")).toHaveAttribute("alt", expect.stringContaining("imagem provisória"));
      expect(within(photo as HTMLElement).getByText("Imagem provisória")).toBeInTheDocument();
    });
    expect(within(photos[3] as HTMLElement).getByRole("img")).toHaveAttribute("alt", expect.stringContaining("Campus das Gambelas"));
    expect(within(photos[3] as HTMLElement).getByText("Fotografia: UAlg")).toBeInTheDocument();
  });
});
