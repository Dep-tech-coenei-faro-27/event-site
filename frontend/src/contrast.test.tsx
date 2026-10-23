/// <reference types="node" />
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import ProtectedRoute from "./components/ProtectedRoute";
import { contrastRatio } from "./utils/contrast";

vi.mock("./utils/useAuth", () => ({
  useAuth: () => ({ user: null, loading: true, refresh: vi.fn(), logout: vi.fn() }),
}));

afterEach(cleanup);

/** As cores do tailwind.config.js, lidas do ficheiro: a tabela não pode divergir da paleta. */
const PALETTE: Record<string, string> = Object.fromEntries(
  [...readFileSync(join(import.meta.dirname, "..", "tailwind.config.js"), "utf8").matchAll(/'([a-z0-9-]+)':\s*'(#[0-9A-Fa-f]{6})'/g)].map(
    (m) => [m[1], m[2]],
  ),
);

const AA = 4.5;

// Pares texto/fundo usados no site. Fundos: as superfícies escuras (o `--bg` das páginas é azul-base,
// `--panel` é azul-painel, `--surface` é azul-superficie, `--panel-strong` é azul-elevado).
// Textos: `--text` branco, `--muted` cinza-texto, `--subtle` cinza-subtil, os acentos e os estados.
const BACKGROUNDS = ["azul-noite", "azul-base", "azul-superficie", "azul-painel", "azul-faq", "azul-elevado"];
const TEXTS = [
  "branco", "gelo", "cinza-texto", "nevoa-azul", "cinza-subtil", "acento-principal", "acento-forte",
  "ciano-digital", "verde-agua", "pervinca", "indigo-beneficio", "ouro", "coral-vivo",
];
// Texto escuro sobre botões e etiquetas em ciano.
const ON_ACCENT: [string, string][] = [
  ["texto-de-acao", "acento-principal"],
  ["texto-sobre-ciano", "acento-forte"],
  ["azul-base", "acento-principal"], // ligação «Saltar para o conteúdo»
];

const PAIRS: [string, string][] = [...TEXTS.flatMap((t) => BACKGROUNDS.map((b) => [t, b] as [string, string])), ...ON_ACCENT];

describe("contraste texto/fundo (WCAG AA, ≥ 4,5:1)", () => {
  it("a fórmula bate com os valores de referência", () => {
    expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 5);
    expect(contrastRatio("#777777", "#FFFFFF")).toBeCloseTo(4.48, 2);
    expect(contrastRatio("#000", "#050D21")).toBeCloseTo(1.09, 2); // o «A carregar» antigo
  });

  it.each(PAIRS)("%s sobre %s", (text, bg) => {
    expect(PALETTE[text], text).toBeDefined();
    expect(PALETTE[bg], bg).toBeDefined();
    expect(contrastRatio(PALETTE[text], PALETTE[bg])).toBeGreaterThanOrEqual(AA);
  });
});

describe("«A carregar…» da área privada", () => {
  it("usa uma cor de texto da paleta com contraste ≥ 4,5:1 sobre o fundo azul-base, e é anunciado", () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<p>privado</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(/a carregar/i);
    const color = [...status.classList].find((c) => c.startsWith("text-") && PALETTE[c.slice(5)]);
    expect(color, `classe text-* da paleta em "${status.className}"`).toBeDefined();
    expect(contrastRatio(PALETTE[color!.slice(5)], PALETTE["azul-base"])).toBeGreaterThanOrEqual(AA);
  });
});
