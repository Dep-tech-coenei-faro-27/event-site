/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Agenda, { SAVED_KEY } from "./Agenda";
import { AGENDA, AGENDA_DAYS, itemsOfDay, type AgendaItem } from "../content/agenda";

// O CSS não se importa com `?raw` nos testes (o vitest devolve-o vazio): lê-se do disco.
const agendaCss = readFileSync(join(import.meta.dirname, "..", "agenda.css"), "utf8");

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  document.body.removeAttribute("data-page");
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function Where() {
  const { search } = useLocation();
  return <span data-testid="search">{search}</span>;
}

const open = (path = "/agenda", props: { renderAction?: (item: AgendaItem) => React.ReactNode } = {}) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <main>
        <Agenda {...props} />
      </main>
      <Where />
    </MemoryRouter>,
  );

const cards = () => [...document.querySelectorAll<HTMLElement>(".ag-card")];
const titles = () => cards().map((c) => c.querySelector("h3")!.textContent);
const result = () => document.querySelector("[data-ag-result]")!.textContent;
const filter = (name: string) => screen.getByRole("button", { name: new RegExp(`^${name}`) });
const dayCount = (key: string) => itemsOfDay(AGENDA, AGENDA_DAYS.find((d) => d.key === key)!).length;

describe("Agenda: dia", () => {
  it("abre na sexta-feira, o primeiro dia completo, e conta as sessões do dia", () => {
    open();
    expect(screen.getByRole("tab", { name: /SEXTA/ })).toHaveAttribute("aria-selected", "true");
    expect(cards()).toHaveLength(dayCount("sexta"));
    expect(result()).toBe(`Sexta-feira, 2 abril · ${dayCount("sexta")} sessões`);
  });

  it.each([
    ["quinta", "QUINTA"],
    ["sabado", "SÁBADO"],
    ["domingo", "DOMINGO"],
  ])("?dia=%s abre nesse dia", (key, tab) => {
    open(`/agenda?dia=${key}`);
    expect(screen.getByRole("tab", { name: new RegExp(tab) })).toHaveAttribute("aria-selected", "true");
    expect(cards()).toHaveLength(dayCount(key));
  });

  it.each(["", "?dia=segunda", "?dia=", "?dia=SEXTA", "?dia=__proto__"])("%s (dia que não existe) abre na sexta-feira", (query) => {
    open(`/agenda${query}`);
    expect(screen.getByRole("tab", { name: /SEXTA/ })).toHaveAttribute("aria-selected", "true");
  });

  it("mudar de dia põe ?dia= no endereço (sem empilhar histórico) e mantém o resto da pesquisa", () => {
    open("/agenda?ref=x");
    fireEvent.click(screen.getByRole("tab", { name: /SÁBADO/ }));
    expect(screen.getByTestId("search").textContent).toBe("?ref=x&dia=sabado");
    expect(cards()).toHaveLength(dayCount("sabado"));
  });

  it("só o separador ativo tem tabindex 0, e as setas, Início e Fim passam de um ao outro com o foco", () => {
    open();
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((t) => t.tabIndex)).toEqual([-1, 0, -1, -1]);
    tabs[1].focus();
    fireEvent.keyDown(tabs[1], { key: "ArrowDown" });
    expect(tabs[2]).toHaveAttribute("aria-selected", "true");
    expect(document.activeElement).toBe(tabs[2]);
    expect(tabs.map((t) => t.tabIndex)).toEqual([-1, -1, 0, -1]);
    fireEvent.keyDown(tabs[2], { key: "ArrowUp" });
    expect(document.activeElement).toBe(tabs[1]);
    fireEvent.keyDown(tabs[1], { key: "Home" });
    expect(document.activeElement).toBe(tabs[0]);
    fireEvent.keyDown(tabs[0], { key: "ArrowLeft" });
    expect(document.activeElement).toBe(tabs[3]);
    fireEvent.keyDown(tabs[3], { key: "ArrowRight" });
    expect(document.activeElement).toBe(tabs[0]);
    fireEvent.keyDown(tabs[0], { key: "a" });
    expect(document.activeElement).toBe(tabs[0]);
  });

  it("os separadores apontam para o painel e o painel para o separador do dia escolhido", () => {
    open();
    const panel = screen.getByRole("tabpanel");
    for (const tab of screen.getAllByRole("tab")) expect(tab.getAttribute("aria-controls")).toBe(panel.id);
    expect(panel.getAttribute("aria-labelledby")).toBe("ag-tab-sexta");
    fireEvent.click(screen.getByRole("tab", { name: /QUINTA/ }));
    expect(screen.getByRole("tabpanel").getAttribute("aria-labelledby")).toBe("ag-tab-quinta");
  });
});

describe("Agenda: filtros e pesquisa", () => {
  it("«Palestras» inclui os workshops, «Workshops» só os workshops, «Tudo» repõe tudo", () => {
    open();
    const all = cards().length;
    fireEvent.click(filter("Palestras"));
    expect(filter("Palestras")).toHaveAttribute("aria-pressed", "true");
    expect(filter("Tudo")).toHaveAttribute("aria-pressed", "false");
    const speakerCards = cards().filter((c) => c.dataset.category !== "encontro").length;
    expect(cards()).toHaveLength(speakerCards);
    expect(cards().length).toBeLessThan(all);
    fireEvent.click(filter("Workshops"));
    expect(cards().length).toBeGreaterThan(0);
    expect(cards().every((c) => c.dataset.category === "workshops")).toBe(true);
    expect(cards().length).toBeLessThan(speakerCards);
    fireEvent.click(filter("Tudo"));
    expect(cards()).toHaveLength(all);
  });

  it("a pesquisa ignora acentos e maiúsculas e procura em horas, tipo, título, local e orador", () => {
    open();
    const search = screen.getByRole("searchbox", { name: "Pesquisar sessões" });
    fireEvent.change(search, { target: { value: "ALMOCO" } });
    expect(titles()).toEqual(["Almoço"]);
    fireEvent.change(search, { target: { value: "dr why" } });
    expect(titles()).toEqual(["Dr Why"]);
    fireEvent.change(search, { target: { value: "12:00" } });
    expect(titles()).toContain("Almoço");
    fireEvent.change(search, { target: { value: "auditorio" } });
    expect(titles().length).toBeGreaterThan(0);
    fireEvent.change(search, { target: { value: "  salas  " } });
    expect(titles()).toEqual(["Atividades"]);
  });

  it("a pesquisa encontra também pela hora de fim", () => {
    open();
    // o almoço de sexta acaba às 14:00 e nenhum item começa a essa hora: só se acha pela hora de fim
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "14:00" } });
    expect(titles()).toEqual(["Almoço"]);
  });

  it("a linha de resultados usa o singular com uma sessão e o plural nas outras", () => {
    open();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "almoco" } });
    expect(result()).toBe("Sexta-feira, 2 abril · 1 sessão");
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "zzz" } });
    expect(result()).toBe("Sexta-feira, 2 abril · 0 sessões");
  });

  it("sem resultados mostra o estado vazio, e «Ver todas as sessões» limpa o filtro e a pesquisa e leva o foco para «Tudo»", () => {
    open();
    const empty = document.querySelector<HTMLElement>(".ag-empty")!;
    expect(empty.hidden).toBe(true);
    fireEvent.click(filter("Workshops"));
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "zzz" } });
    expect(empty.hidden).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Ver todas as sessões" }));
    expect(empty.hidden).toBe(true);
    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(filter("Tudo")).toHaveAttribute("aria-pressed", "true");
    expect(document.activeElement).toBe(filter("Tudo"));
    expect(cards()).toHaveLength(dayCount("sexta"));
  });

  it("o filtro e a pesquisa ficam ao mudar de dia", () => {
    open();
    fireEvent.click(filter("Workshops"));
    fireEvent.click(screen.getByRole("tab", { name: /SÁBADO/ }));
    expect(filter("Workshops")).toHaveAttribute("aria-pressed", "true");
    expect(cards().every((c) => c.dataset.category === "workshops")).toBe(true);
  });
});

describe("Agenda: sessões guardadas", () => {
  const firstSave = () => cards()[0].querySelector<HTMLButtonElement>(".ag-save")!;

  it("guardar marca o botão, conta nos «Guardados», grava no dispositivo e avisa; remover desfaz tudo", () => {
    open();
    const id = cards()[0].id;
    expect(firstSave()).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(firstSave());
    expect(firstSave()).toHaveAttribute("aria-pressed", "true");
    expect(firstSave().getAttribute("aria-label")).toMatch(/^Remover dos guardados: /);
    expect(JSON.parse(localStorage.getItem(SAVED_KEY)!)).toEqual([id]);
    expect(filter("Guardados")).toHaveTextContent("Guardados 1");
    expect(screen.getByRole("status")).toHaveTextContent("Sessão guardada neste dispositivo.");
    fireEvent.click(firstSave());
    expect(JSON.parse(localStorage.getItem(SAVED_KEY)!)).toEqual([]);
    expect(filter("Guardados")).toHaveTextContent("Guardados 0");
    expect(screen.getByRole("status")).toHaveTextContent("Sessão removida dos guardados.");
  });

  it("o aviso desaparece sozinho ao fim de uns segundos", () => {
    vi.useFakeTimers();
    open();
    fireEvent.click(firstSave());
    expect(document.querySelector(".ag-toast")).toHaveClass("is-visible");
    act(() => {
      vi.advanceTimersByTime(2400);
    });
    expect(document.querySelector(".ag-toast")).not.toHaveClass("is-visible");
  });

  it("«Guardados» mostra só as guardadas, de qualquer dia, e abre com as de uma visita anterior", () => {
    const sat = itemsOfDay(AGENDA, AGENDA_DAYS[2])[0].id;
    localStorage.setItem(SAVED_KEY, JSON.stringify([sat]));
    open();
    expect(filter("Guardados")).toHaveTextContent("Guardados 1");
    fireEvent.click(filter("Guardados"));
    expect(cards()).toHaveLength(0);
    fireEvent.click(screen.getByRole("tab", { name: /SÁBADO/ }));
    expect(cards().map((c) => c.id)).toEqual([sat]);
  });

  it.each([
    ["JSON estragado", "{nope"],
    ["não é uma lista", '{"a":1}'],
    ["lista com lixo e identificadores que já não existem", '[1,null,"nao-existe"]'],
  ])("armazenamento com %s não rebenta e conta zero", (_name, value) => {
    localStorage.setItem(SAVED_KEY, value);
    open();
    expect(filter("Guardados")).toHaveTextContent("Guardados 0");
    expect(cards().length).toBeGreaterThan(0);
  });

  it("ao guardar outra sessão, os identificadores que já não existem na agenda não ficam gravados", () => {
    const ids = itemsOfDay(AGENDA, AGENDA_DAYS[1]).map((i) => i.id);
    localStorage.setItem(SAVED_KEY, JSON.stringify(["sessao-que-ja-nao-existe", ids[1]]));
    open();
    fireEvent.click(cards()[0].querySelector<HTMLButtonElement>(".ag-save")!);
    expect(JSON.parse(localStorage.getItem(SAVED_KEY)!).sort()).toEqual([ids[0], ids[1]].sort());
  });

  it("sem armazenamento (privado ou cheio) guardar continua a funcionar nesta visita", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("cheio", "QuotaExceededError");
    });
    open();
    fireEvent.click(firstSave());
    expect(firstSave()).toHaveAttribute("aria-pressed", "true");
    expect(filter("Guardados")).toHaveTextContent("Guardados 1");
    vi.restoreAllMocks();
  });
});

describe("Agenda: o cartão leva tudo e não tem «Ver mais»", () => {
  it("mostra a hora de início e de fim (com o fuso de Lisboa), o tipo, o título, o orador e o local", () => {
    open();
    const card = cards().find((c) => c.id === "sex-1100-palestra")!;
    const times = card.querySelectorAll("time");
    expect([...times].map((t) => t.textContent)).toEqual(["11:00", "12:00"]);
    expect([...times].map((t) => t.getAttribute("datetime"))).toEqual(["2027-04-02T11:00+01:00", "2027-04-02T12:00+01:00"]);
    expect(card.querySelector(".ag-card__time")).toHaveTextContent("11:00 – 12:00");
    expect(card.querySelector(".ag-card__kind")).toHaveTextContent("Palestra");
    expect(within(card).getByRole("heading", { name: "Palestra" })).toBeInTheDocument();
    expect(card).toHaveTextContent("Orador a anunciar");
    expect(card).toHaveTextContent("Auditório a confirmar");
  });

  it("um item sem hora de fim mostra só a hora de início", () => {
    const items: AgendaItem[] = [{ id: "sex-2300-sem-fim", start: "2027-04-02T23:00", title: "Sem fim", kind: "Noite", category: "encontro" }];
    render(
      <MemoryRouter initialEntries={["/agenda"]}>
        <main>
          <Agenda items={items} />
        </main>
      </MemoryRouter>,
    );
    const last = cards().at(-1)!;
    expect(last.querySelectorAll("time")).toHaveLength(1);
    expect(last.querySelector(".ag-card__time")?.textContent).toMatch(/^\d\d:\d\d$/);
  });

  it("não há botão «Ver mais» nem «Detalhes», nem janela de detalhes", () => {
    open();
    expect(screen.queryByRole("button", { name: /ver mais|ver detalhes|detalhes/i })).toBeNull();
    expect(document.querySelector("dialog")).toBeNull();
    for (const card of cards()) expect(card.querySelector("button[aria-expanded]")).toBeNull();
  });

  it("os momentos têm o azulejo do site (CSS, sem imagem) e as palestras e workshops o retrato por anunciar", () => {
    open();
    const moment = cards().find((c) => c.dataset.category === "encontro")!;
    expect(within(moment).queryByRole("img")).toBeNull();
    expect(moment.querySelector(".ag-card__media--moment")).not.toBeNull();
    expect(moment.querySelector(".ag-card__media img")).toBeNull();
    const rule = agendaCss.slice(agendaCss.indexOf(".ag-card__media--moment::before"));
    expect(rule.slice(0, rule.indexOf("}"))).toMatch(/azulejo-pattern-transparent\.webp/);
    expect(moment).toHaveTextContent("Local a confirmar");
    const speaker = cards().find((c) => c.dataset.category !== "encontro")!;
    expect(within(speaker).getByRole("img", { name: "Retrato do orador por anunciar" })).toBeInTheDocument();
  });

  it("os cartões do primeiro dia levam a cor azul; os dos outros dias, a da categoria", () => {
    open("/agenda?dia=quinta");
    expect(cards().length).toBeGreaterThan(0);
    expect(cards().every((c) => c.classList.contains("ag-card--azul"))).toBe(true);
    cleanup();
    open("/agenda?dia=sexta");
    expect(cards().some((c) => c.classList.contains("ag-card--azul"))).toBe(false);
    // a regra da cor azul vem depois das das categorias, para ganhar a «encontro» (areia) do primeiro dia
    expect(agendaCss.indexOf("ag-card--azul {")).toBeGreaterThan(agendaCss.indexOf("ag-card--workshops {"));
    expect(agendaCss.slice(agendaCss.indexOf("ag-card--azul {"))).toMatch(/^ag-card--azul {\s*--tone: #1ab2ff;/);
  });

  it("o tipo da sessão é texto simples, sem contorno nem fundo (nada de pílula)", () => {
    const rule = (selector: string) => {
      const start = agendaCss.indexOf(selector + " {");
      return agendaCss.slice(start, agendaCss.indexOf("}", start));
    };
    const kind = rule('body[data-page="agenda"] main .ag-card__kind');
    expect(kind.length).toBeGreaterThan(0);
    expect(kind).not.toMatch(/border|background|border-radius/);
    open();
    expect(document.querySelector(".ag-card__kind")!.tagName).toBe("SPAN");
  });
});

describe("Agenda: filtros em ecrã estreito", () => {
  const rule = (selector: string) => {
    const start = agendaCss.indexOf(selector + " {");
    return agendaCss.slice(start, agendaCss.indexOf("}", start));
  };

  it("as pílulas dos filtros ficam numa só linha, com scroll horizontal quando não cabem (nunca passam para uma segunda linha)", () => {
    const filters = rule('body[data-page="agenda"] main .ag-filters');
    expect(filters).toMatch(/flex-wrap: nowrap/);
    expect(filters).toMatch(/overflow-x: auto/);
    expect(filters).toMatch(/min-width: 0/);
    expect(filters).not.toMatch(/flex-wrap: wrap/);
    const pill = rule('body[data-page="agenda"] main .ag-filters button');
    expect(pill).toMatch(/flex: none/);
    expect(pill).toMatch(/white-space: nowrap/);
  });

  it("no telemóvel a linha dos filtros ocupa a largura toda (e a pesquisa vai para a linha de baixo)", () => {
    const mobile = agendaCss.slice(agendaCss.indexOf("@media (max-width: 700px)"));
    expect(mobile).toMatch(/\.ag-filters \{\s*flex: 1 1 100%;/);
  });
});

describe("Agenda: o espaço da ação (inscrição, compra…)", () => {
  const workshopsOnly = (item: AgendaItem) =>
    item.category === "workshops" ? (
      <button type="button" className="ag-action">
        Inscrever-me
      </button>
    ) : null;

  it("sem `renderAction` não há nenhum botão, e todos os cartões têm o mesmo pé reservado", () => {
    open();
    expect(document.querySelector("[data-slot=action]")).toBeNull();
    expect(document.querySelector(".ag-list--actions")).toBeNull();
    for (const card of cards()) expect(card.querySelector(".ag-card__foot")).not.toBeNull();
  });

  it("o botão de um item aparece no canto do pé desse cartão e só nele", () => {
    open("/agenda", { renderAction: workshopsOnly });
    const withAction = cards().filter((c) => c.querySelector("[data-slot=action]"));
    expect(withAction.length).toBeGreaterThan(0);
    expect(withAction.every((c) => c.dataset.category === "workshops")).toBe(true);
    for (const card of withAction) {
      expect(card.querySelector(".ag-card__foot [data-slot=action] button.ag-action")).toHaveTextContent("Inscrever-me");
    }
    expect(document.querySelector(".ag-list--actions")).not.toBeNull();
    // todos os cartões, com ou sem botão, têm o mesmo pé
    for (const card of cards()) expect(card.querySelectorAll(".ag-card__foot")).toHaveLength(1);
  });

  it("um dia em que nenhum item tem botão não reserva o espaço extra do telemóvel", () => {
    open("/agenda?dia=quinta", { renderAction: workshopsOnly });
    expect(document.querySelector(".ag-list--actions")).toBeNull();
  });

  it("os cartões têm todos a mesma altura mínima e o pé a altura de um botão (o botão é o antigo «Ver mais»)", () => {
    const rule = (selector: string) => {
      const start = agendaCss.indexOf(selector + " {");
      return agendaCss.slice(start, agendaCss.indexOf("}", start));
    };
    expect(rule('body[data-page="agenda"] main .ag-card')).toMatch(/min-height: 200px/);
    expect(rule('body[data-page="agenda"] main .ag-card__foot')).toMatch(/min-height: 50px/);
    const action = rule('body[data-page="agenda"] main .ag-action');
    expect(action).toMatch(/height: 38px/);
    expect(action).toMatch(/padding: 0 16px/);
    expect(action).toMatch(/border: 1px solid rgba\(26, 178, 255, 0\.42\)/);
    expect(action).toMatch(/background: rgba\(26, 178, 255, 0\.08\)/);
  });
});

describe("Agenda: texto da página", () => {
  it("tem o texto do desenho: título, nota final, fecho com as duas ligações, sem Plataforma nem `aside`", () => {
    open();
    expect(screen.getByRole("heading", { level: 1, name: "Encontra a tua próxima ideia." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Quatro dias, um programa completo." })).toBeInTheDocument();
    expect(screen.getByText(/Os perfis dos oradores serão publicados após confirmação\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Descobrir os bilhetes" })).toHaveAttribute("href", "/bilhetes");
    expect(screen.getByRole("link", { name: "Tenho uma dúvida" })).toHaveAttribute("href", "/informacao-ajuda");
    expect(screen.queryByText(/plataforma/i)).toBeNull();
    // um `aside` dentro do `main` é um marco «complementar» fora do nível superior (axe: landmark-complementary-is-top-level)
    expect(document.querySelector("aside")).toBeNull();
  });
});
