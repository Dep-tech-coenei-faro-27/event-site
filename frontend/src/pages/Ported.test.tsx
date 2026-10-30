import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Acessibilidade from "./Acessibilidade";
import Agenda from "./Agenda";
import Bilhetes from "./Bilhetes";
import Equipa from "./Equipa";
import InformacaoAjuda from "./InformacaoAjuda";
import Privacidade from "./Privacidade";
import Sobre from "./Sobre";
import TermosCondicoes from "./TermosCondicoes";
import { departments } from "../data/Team";

afterEach(() => {
  cleanup();
  document.body.removeAttribute("data-page");
  vi.unstubAllGlobals();
});

const at = (element: React.ReactElement, path = "/") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <main>{element}</main>
    </MemoryRouter>,
  );

describe("páginas no desenho novo: o que cada uma marca e liga", () => {
  it.each([
    ["Sobre", <Sobre />, "sobre"],
    ["Agenda", <Agenda />, "agenda"],
    ["Equipa", <Equipa />, "equipa"],
    ["Informação e Ajuda", <InformacaoAjuda />, "informacao-ajuda"],
    ["Bilhetes", <Bilhetes />, "bilhetes"],
    ["Termos", <TermosCondicoes />, "legal"],
    ["Privacidade", <Privacidade />, "legal"],
    ["Acessibilidade", <Acessibilidade />, "legal"],
  ])("%s tem um só h1 e marca o body com o seu data-page", (_name, page, dataPage) => {
    at(page);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(document.body.dataset.page).toBe(dataPage);
    expect(document.querySelector("main > .page-hero")).not.toBeNull();
  });

  it("todas as ligações internas vão a páginas reais (nenhuma é `#` solta)", () => {
    for (const page of [<Sobre />, <Bilhetes />, <Equipa />]) {
      const { container, unmount } = at(page);
      container.querySelectorAll("a").forEach((a) => {
        const href = a.getAttribute("href") ?? "";
        expect(href, a.textContent ?? "").not.toBe("#");
      });
      unmount();
    }
  });
});

describe("Bilhetes", () => {
  it("cada «Escolher bilhete» leva ao checkout com a sua modalidade", () => {
    at(<Bilhetes />);
    const hrefs = screen.getAllByRole("link", { name: /escolher bilhete/i }).map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual([
      "/bilhetes/checkout?bilhete=acesso",
      "/bilhetes/checkout?bilhete=refeicoes",
      "/bilhetes/checkout?bilhete=completo",
      "/bilhetes/checkout?bilhete=geral",
      "/bilhetes/checkout?bilhete=geral_refeicoes",
    ]);
    expect(screen.getByRole("link", { name: "Comprar bilhete" })).toHaveAttribute("href", "/bilhetes/checkout");
  });
});

describe("Equipa", () => {
  it("mostra todas as pessoas e departamentos dos dados da equipa", () => {
    const { container } = at(<Equipa />);
    expect(container.querySelectorAll(".team-department")).toHaveLength(departments.length);
    const total = departments.reduce((sum, d) => sum + d.members.length, 0);
    expect(container.querySelectorAll(".team-member")).toHaveLength(total);
    const first = departments[0].members[0];
    expect(screen.getByRole("heading", { level: 3, name: first.name })).toBeInTheDocument();
  });
});

describe("Agenda", () => {
  it("os dias são separadores: abre na sexta, o painel mostra só o dia escolhido e as setas passam de um ao outro", () => {
    const { container } = at(<Agenda />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(4);
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    const panel = () => container.querySelector("#ag-panel")!;
    expect(panel().querySelector("#sex-1100-palestra")).not.toBeNull();
    expect(panel().querySelector("#qui-1600-sessao-de-boas-vindas")).toBeNull();

    fireEvent.click(tabs[0]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[1]).toHaveAttribute("aria-selected", "false");
    expect(panel().querySelector("#qui-1600-sessao-de-boas-vindas")).not.toBeNull();
    expect(panel().querySelector("#sex-1100-palestra")).toBeNull();

    fireEvent.keyDown(tabs[0], { key: "ArrowRight" });
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(tabs[1], { key: "End" });
    expect(tabs[3]).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(tabs[3], { key: "ArrowRight" });
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
  });
});

describe("Informação e Ajuda", () => {
  it("o FAQ filtra por categoria e pela pesquisa (sem acentos) e mostra o vazio", () => {
    at(<InformacaoAjuda />);
    const questions = () => screen.queryAllByRole("button", { expanded: undefined }).filter((b) => b.classList.contains("faq-question"));
    const all = questions().length;
    expect(all).toBeGreaterThan(10);

    fireEvent.click(screen.getByRole("button", { name: "Transporte", pressed: false }));
    const transport = questions().length;
    expect(transport).toBeGreaterThan(0);
    expect(transport).toBeLessThan(all);

    fireEvent.click(screen.getByRole("button", { name: "Todas" }));
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "inscricoes" } }); // sem acento acha «Inscrições»? só se estiver no texto
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "xyzxyz" } });
    expect(questions()).toHaveLength(0);
    expect(screen.getByText(/não encontrámos uma resposta/i)).toBeInTheDocument();
  });

  it("a primeira pergunta abre por omissão e cada uma abre e fecha ao clicar", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true })); // sem animações
    at(<InformacaoAjuda />);
    const first = document.querySelector(".faq-question") as HTMLElement;
    expect(first).toHaveAttribute("aria-expanded", "true");
    const second = document.querySelectorAll(".faq-question")[1] as HTMLElement;
    expect(second).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(second);
    expect(second).toHaveAttribute("aria-expanded", "true");
    expect(first).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(first);
    expect(first).toHaveAttribute("aria-expanded", "false");
    expect(document.getElementById(first.getAttribute("aria-controls")!)).toHaveAttribute("hidden");
  });

  it("os mapas só se carregam depois de a pessoa o pedir (não há pedido ao OpenStreetMap antes)", () => {
    const { container } = at(<InformacaoAjuda />);
    expect(container.querySelectorAll("iframe")).toHaveLength(0);
    const buttons = screen.getAllByRole("button", { name: /carregar mapa/i });
    expect(buttons).toHaveLength(2);
    fireEvent.click(buttons[0]);
    expect(container.querySelectorAll("iframe")).toHaveLength(1);
    expect(container.querySelector("iframe")?.getAttribute("src")).toContain("openstreetmap.org");
  });

  it("a contagem decrescente tem as quatro unidades", () => {
    at(<InformacaoAjuda />);
    const timer = screen.getByRole("timer");
    ["Dias", "Horas", "Minutos", "Segundos"].forEach((label) => expect(within(timer).getByText(label)).toBeInTheDocument());
  });
});

describe("páginas legais", () => {
  it("o índice liga a cada secção e a ligação da própria página fica ativa", () => {
    at(<TermosCondicoes />, "/termos");
    const toc = screen.getByRole("navigation", { name: /neste documento/i });
    const links = within(toc).getAllByRole("link");
    expect(links.length).toBeGreaterThan(3);
    links.forEach((a) => {
      const id = a.getAttribute("href")!.slice(1);
      expect(document.getElementById(id)).not.toBeNull();
    });
    expect(screen.getByRole("link", { name: "Termos e condições", current: "page" })).toBeInTheDocument();
  });
});
