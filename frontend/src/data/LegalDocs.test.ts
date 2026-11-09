import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { LEGAL_DOCS, formatLegalDate } from "./LegalDocs";

describe("documentos legais: versão e data numa só fonte", () => {
  it("escreve a data por extenso", () => {
    expect(formatLegalDate("2026-11-06")).toBe("6 de novembro de 2026");
    expect(formatLegalDate("2026-10-08")).toBe("8 de outubro de 2026");
  });

  it("a versão dos termos que o servidor guarda ao registar é a que as páginas mostram", () => {
    const service = readFileSync(resolve(__dirname, "../../../backend/app/domains/users/service.py"), "utf-8");
    const stored = service.match(/CURRENT_TERMS_VERSION\s*=\s*"([^"]+)"/)?.[1];
    expect(stored).toBe(LEGAL_DOCS.termos.version);
  });

  it("nenhuma página volta a escrever a versão ou a data à mão", () => {
    for (const file of ["TermosCondicoes", "Privacidade", "Acessibilidade", "Registo"]) {
      const source = readFileSync(resolve(__dirname, `../pages/${file}.tsx`), "utf-8");
      expect(source, file).not.toMatch(/version="/);
      expect(source, file).not.toMatch(/lastUpdated(ISO)?="/);
      expect(source, file).not.toMatch(/versão \d/);
    }
  });
});
