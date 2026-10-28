/// <reference types="vite/client" />
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import { renderRoute } from "../test/routes";

vi.mock("../utils/useAuth", () => ({
  useAuth: () => ({ user: null, loading: false, refresh: vi.fn(), logout: vi.fn() }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Parcerias passa para a página inicial", () => {
  it("/parcerias leva à secção de parceiros da página inicial", async () => {
    await renderRoute("/parcerias");
    expect(document.getElementById("parceiros")).not.toBeNull();
    expect(screen.getByRole("heading", { name: /quem apoia o enei/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /quero ser parceiro/i })).toHaveAttribute("href", "mailto:geral@eneiconf.pt");
  });

  it("a barra de topo já não tem Parcerias e o rodapé liga à secção de parceiros", () => {
    render(
      <MemoryRouter>
        <Navbar />
        <Footer />
      </MemoryRouter>,
    );
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(within(nav).queryByRole("link", { name: "Parcerias" })).toBeNull();
    expect(screen.getByRole("link", { name: "Parceiros" })).toHaveAttribute("href", "/#parceiros");
  });
});

describe("endereços de contacto", () => {
  it("nenhum endereço @enei.pt sobrou no código (o domínio do evento é eneiconf.pt)", () => {
    const sources = import.meta.glob("../**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    const offenders = Object.entries(sources)
      .filter(([file]) => !file.includes(".test."))
      .filter(([, text]) => /@enei\.pt/.test(text))
      .map(([file]) => file);
    expect(offenders).toEqual([]);
  });
});
