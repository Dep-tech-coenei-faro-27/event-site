/// <reference types="node" />
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

// Lê o código-fonte dos estilos e dos componentes (o jsdom não aplica o CSS nem calcula o foco).
// O Vitest entrega os .css vazios (mesmo com ?raw), por isso estes leem-se do disco.
const SRC = import.meta.dirname;
const css: Record<string, string> = Object.fromEntries(
  readdirSync(SRC, { recursive: true, encoding: "utf8" })
    .filter((f) => f.endsWith(".css"))
    .map((f) => [relative(SRC, join(SRC, f)), readFileSync(join(SRC, f), "utf8")]),
);
const tsx = import.meta.glob(["./**/*.tsx", "!./**/*.test.tsx"], { query: "?raw", import: "default", eager: true }) as Record<
  string,
  string
>;

type Rule = { file: string; selectors: string[]; body: string };

/** Regras mais interiores (`seletor { declarações }`), também as que estão dentro de @media. */
function rules(): Rule[] {
  const out: Rule[] = [];
  for (const [file, source] of Object.entries(css)) {
    const clean = source.replace(/\/\*[\s\S]*?\*\//g, "");
    for (const m of clean.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const selectors = m[1].split(",").map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean);
      out.push({ file, selectors, body: m[2] });
    }
  }
  return out;
}

const removesOutline = (body: string) => /(^|;|\s)outline\s*:\s*(none|0)\s*(;|$)/.test(body);
const drawsOutline = (body: string) => /(^|;|\s)outline\s*:\s*(?!none|0\s*(;|$))[^;]+/.test(body);

describe("foco visível: cada `outline: none` tem um substituto", () => {
  const all = rules();
  const withoutOutline = all.flatMap((r) => (removesOutline(r.body) ? r.selectors.map((s) => ({ file: r.file, selector: s })) : []));

  it("encontra os seletores que tiram o contorno (o teste vê o CSS)", () => {
    expect(withoutOutline.length).toBeGreaterThan(0);
  });

  it.each(withoutOutline.map((x) => [`${x.file}: ${x.selector}`, x.selector]))(
    "%s desenha um contorno em :focus-visible",
    (_label, selector) => {
      const substitute = all.find((r) => r.selectors.includes(`${selector}:focus-visible`) && drawsOutline(r.body));
      expect(substitute, `${selector}:focus-visible { outline: … }`).toBeDefined();
    },
  );

  it("cada classe `outline-none` dos componentes vem com `focus-visible:outline`", () => {
    const offenders: string[] = [];
    for (const [file, source] of Object.entries(tsx)) {
      for (const m of source.matchAll(/className=(?:"([^"]*)"|\{`([^`]*)`\})/g)) {
        const classes = m[1] ?? m[2];
        if (/(^|\s)outline-none(\s|$)/.test(classes) && !/(^|\s)focus-visible:outline(\s|-)/.test(classes)) {
          offenders.push(file);
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});
