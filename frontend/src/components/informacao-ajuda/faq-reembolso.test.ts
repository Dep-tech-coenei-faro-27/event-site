import { describe, expect, it } from "vitest";
import { FAQ_DATA } from "./faqData";

describe("FAQ: reembolso", () => {
  const item = FAQ_DATA.find((entry) => /reembolso do bilhete/i.test(entry.question));

  it("há uma pergunta sobre o reembolso, em Inscrições, que diz o mesmo que os termos", () => {
    expect(item?.category).toBe("inscricoes");
    expect(item?.answer).toMatch(/não depois de o bilhete estar emitido/i);
    expect(item?.answer).toMatch(/cancelado por nós, o dinheiro volta todo/i);
    expect(item?.answer).toMatch(/o reembolso é parcial/i);
    expect(item?.answer).toContain("geral@eneiconf.pt");
  });

  it("não promete prazo nem transferência do bilhete", () => {
    expect(item?.answer).not.toMatch(/\d+\s*dias|transfer/i);
  });

  it("os identificadores das perguntas continuam únicos", () => {
    const ids = FAQ_DATA.map((entry) => entry.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
