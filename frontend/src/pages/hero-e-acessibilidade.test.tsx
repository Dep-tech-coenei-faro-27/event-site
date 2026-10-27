/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { cleanup, render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

// O CSS não se importa com `?raw` nos testes (o vitest devolve-o vazio): lê-se do disco.
const css = (name: string) => readFileSync(join(import.meta.dirname, "..", name), "utf8");

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const at = (element: React.ReactElement, path = "/") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <main>{element}</main>
    </MemoryRouter>,
  );

describe("Declaração de acessibilidade", () => {
  it("declara a exceção de contraste das caixas finais em vez de prometer contraste em todo o lado", async () => {
    const { default: Acessibilidade } = await import("./Acessibilidade");
    at(<Acessibilidade />, "/acessibilidade");
    const body = document.body.textContent ?? "";
    expect(body).toMatch(/Exceção conhecida/);
    expect(body).toMatch(/caixas finais/i);
    expect(body).toMatch(/abaixo do mínimo de 4,5:1/);
    expect(body).toMatch(/Versão do texto\s*1\.1/);
  });
});

describe("início: o fim do hero", () => {
  it("a barra de sinal tem uma só cor e o hero não tem a linha por baixo", async () => {
    const { default: Hero } = await import("../components/Hero");
    const indexCss = css("index.css");
    const signal = indexCss.match(/\.hero-signal\s*\{[^}]*\}/s)![0];
    expect(signal).toMatch(/background:\s*var\(--accent\);/);
    expect(signal).not.toMatch(/gradient/);
    const { container } = at(<Hero />);
    expect(container.querySelector(".hero-home")!.className).not.toMatch(/border-b/);
  });

  it("o traço no topo de cada secção é sempre azul (sem passar a lilás a meio)", () => {
    const trace = css("motion.css").match(/\.motion-section__trace\s*\{[^}]*\}/s)![0];
    expect(trace).toMatch(/rgba\(var\(--accent-rgb\), 0\.75\) 30%/);
    expect(trace).not.toMatch(/170,\s*170,\s*255/);
  });

  it("o traço no topo da primeira secção (por baixo do cartão data/local/bilhetes) fica escondido", () => {
    expect(css("home.css")).toMatch(/\.home-edition > \.motion-section__trace\s*\{\s*display: none;/);
  });
});
