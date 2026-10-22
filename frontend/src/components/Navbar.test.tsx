import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Navbar from "./Navbar";

vi.mock("../utils/useAuth", () => ({
  useAuth: () => ({ user: null, loading: false, refresh: vi.fn(), logout: vi.fn() }),
}));

/** Simula a largura do ecrã: `mobile` responde às media queries de largura máxima. */
function stubViewport(mobile: boolean) {
  const listeners = new Set<() => void>();
  const state = { mobile };
  vi.stubGlobal("matchMedia", (query: string) => ({
    get matches() {
      return query.includes("max-width") ? state.mobile : !state.mobile;
    },
    media: query,
    addEventListener: (_: string, fn: () => void) => listeners.add(fn),
    removeEventListener: (_: string, fn: () => void) => listeners.delete(fn),
  }));
  return (next: boolean) => {
    state.mobile = next;
    act(() => listeners.forEach((fn) => fn()));
  };
}

const renderNavbar = () =>
  render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>,
  );

const menuButton = () => screen.getByRole("button", { name: "Menu de navegação" });

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("menu móvel", () => {
  it("aria-controls aponta para o id da navegação, que existe", () => {
    stubViewport(true);
    renderNavbar();
    const id = menuButton().getAttribute("aria-controls");
    expect(id).toBeTruthy();
    const nav = document.getElementById(id!);
    expect(nav).not.toBeNull();
    expect(nav!.tagName).toBe("NAV");
  });

  it("fechado, os links saem da ordem de tabulação; aberto, voltam", () => {
    stubViewport(true);
    renderNavbar();
    const nav = document.getElementById(menuButton().getAttribute("aria-controls")!)!;
    expect(nav).toHaveAttribute("inert");

    fireEvent.click(menuButton());
    expect(menuButton()).toHaveAttribute("aria-expanded", "true");
    expect(nav).not.toHaveAttribute("inert");
  });

  it("Escape fecha o menu e devolve o foco ao botão", () => {
    stubViewport(true);
    renderNavbar();
    fireEvent.click(menuButton());
    const link = screen.getByRole("link", { name: "Agenda" });
    link.focus();
    expect(document.activeElement).toBe(link);

    fireEvent.keyDown(link, { key: "Escape" });
    expect(menuButton()).toHaveAttribute("aria-expanded", "false");
    expect(document.activeElement).toBe(menuButton());
  });

  it("aberto, o Tab a seguir ao botão entra nos links do menu (e não salta para a página)", () => {
    stubViewport(true);
    renderNavbar();
    fireEvent.click(menuButton());
    // Ordem de tabulação = ordem no documento, sem o que está dentro de um `inert`.
    const focusable = [...document.querySelectorAll<HTMLElement>("a[href], button")].filter((el) => !el.closest("[inert]"));
    const next = focusable[focusable.indexOf(menuButton()) + 1];
    expect(next).toHaveTextContent("Sobre");
    expect(next.closest("nav")).not.toBeNull();
  });

  it("Escape com o menu fechado não rouba o foco", () => {
    stubViewport(true);
    renderNavbar();
    const outside = document.createElement("button");
    document.body.appendChild(outside);
    outside.focus();
    fireEvent.keyDown(outside, { key: "Escape" });
    expect(document.activeElement).toBe(outside);
    outside.remove();
  });

  it("no desktop a navegação está sempre na ordem de tabulação", () => {
    const resize = stubViewport(false);
    renderNavbar();
    const nav = document.getElementById(menuButton().getAttribute("aria-controls")!)!;
    expect(nav).not.toHaveAttribute("inert");

    resize(true);
    expect(nav).toHaveAttribute("inert");
    resize(false);
    expect(nav).not.toHaveAttribute("inert");
  });
});
