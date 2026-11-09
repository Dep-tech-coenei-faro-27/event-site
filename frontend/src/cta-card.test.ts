import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// O CSS não se importa com `?raw` nos testes (o vitest devolve-o vazio): lê-se do disco.
const css = (name: string) => readFileSync(join(import.meta.dirname, name), "utf8");

/** A caixa luminosa do fim das páginas tem o desenho num só ficheiro. */
describe("caixa luminosa do fim das páginas", () => {
  it("o degradê está em `cta-card.css`, com o azul-claro a partir dos 75 %", () => {
    expect(css("cta-card.css")).toMatch(/linear-gradient\(125deg, #0062c4, #00aaff 75%, #00c5ff\)/);
  });

  it("nenhuma página repete o degradê nem as regras base da caixa", () => {
    for (const name of ["agenda-base.css", "bilhetes.overrides.css", "equipa.css", "home.css", "sobre.css"]) {
      const text = css(name);
      expect(text, name).not.toMatch(/#00aaff 58%/i);
      expect(text, name).not.toMatch(/\.cta::after/);
      expect(text, name).not.toMatch(/\.cta \.btn--secondary/);
    }
  });
});
