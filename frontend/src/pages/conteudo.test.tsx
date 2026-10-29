/// <reference types="node" />
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { renderRoute } from "../test/routes";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// As páginas que o público vê sem iniciar sessão.
const PUBLIC_PAGES = [
  "/", "/sobre", "/agenda", "/equipa", "/bilhetes", "/informacao-ajuda",
  "/acessibilidade", "/termos", "/privacidade", "/conta", "/conta/criar", "/conta/recuperar",
];

// Texto de marcador de posição que nunca deve chegar ao público.
const PLACEHOLDERS: [string, RegExp][] = [
  ["Lorem ipsum", /lorem ipsum/i],
  ["TBD", /\bTBD\b/],
  ["[…] ou [...]", /\[\s*(…|\.\.\.)\s*\]/],
  ["«exemplo» (texto de exemplo)", /\btexto de exemplo\b|\bnome exemplo\b|\bexemplo de texto\b/i],
  ["«por anunciar» / «a anunciar»", /\b(por|a) anunciar\b/i],
  ["«a confirmar»", /\ba confirmar\b/i],
  ["«Nome · Organização»", /nome\s*·\s*organiza/i],
];

// A Agenda mostra «a anunciar» e «a confirmar» de propósito enquanto o programa é provisório. Sai daqui
// quando a agenda tiver oradores e locais reais (tarefa «Dados reais» da issue de reestruturação do site).
const PROVISIONAL: Record<string, string[]> = {
  "/agenda": ["«por anunciar» / «a anunciar»", "«a confirmar»"],
};

/** O texto como se lê: cada nó de texto separado por um espaço (com `textContent`, «confirmar» cola-se à hora da sessão seguinte). */
function readableText(root: Element): string {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const parts: string[] = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) parts.push(node.textContent ?? "");
  return parts.join(" ");
}

describe("conteúdo provisório", () => {
  it.each(PUBLIC_PAGES)("%s não mostra texto de marcador de posição", async (path) => {
    const { container } = await renderRoute(path);
    const text = readableText(container);
    const allowed = PROVISIONAL[path] ?? [];
    const found = PLACEHOLDERS.filter(([name, re]) => !allowed.includes(name) && re.test(text)).map(([name]) => name);
    expect(found, path).toEqual([]);
  });

  it("a varredura apanha o marcador mesmo colado ao texto seguinte, e a Agenda continua a mostrá-lo (isenção em uso)", async () => {
    const { container } = await renderRoute("/agenda");
    const text = readableText(container);
    expect(container.textContent).toMatch(/confirmar\d\d:\d\d/); // «Salas a confirmar» cola-se à hora da sessão seguinte
    expect(text).toMatch(/\ba confirmar\b/);
    expect(text).toMatch(/\ba anunciar\b/);
  });
});

describe("ligações externas", () => {
  it.each(PUBLIC_PAGES)("%s: as ligações para fora ou que abrem noutro separador levam rel=\"noopener noreferrer\"", async (path) => {
    const { container } = await renderRoute(path);
    const external = [...container.querySelectorAll<HTMLAnchorElement>("a")].filter(
      (a) => a.target === "_blank" || /^https?:\/\//.test(a.getAttribute("href") ?? ""),
    );
    external.forEach((a) => {
      const rel = (a.getAttribute("rel") ?? "").split(/\s+/);
      expect(rel, a.outerHTML).toEqual(expect.arrayContaining(["noopener", "noreferrer"]));
    });
  });
});

describe("peso das imagens", () => {
  // Só a fotografia de grupo usada no hero mantém a qualidade original acima do limite.
  const MAX_BYTES = 900_000;
  const roots = [
    ["frontend/src/assets", join(import.meta.dirname, "..", "assets")],
    ["ui-ux/assets", join(import.meta.dirname, "..", "..", "..", "ui-ux", "assets")],
  ] as const;
  const files = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? files(join(dir, e.name)) : [join(dir, e.name)]));

  it.each(roots)("nenhum ficheiro de %s passa dos 900 kB, exceto equipa.webp", (_name, root) => {
    const tooBig = files(root)
      .map((f) => [f.slice(root.length + 1), statSync(f).size] as const)
      .filter(([file, size]) => file !== "equipa.webp" && size > MAX_BYTES);
    expect(tooBig).toEqual([]);
  });
});
