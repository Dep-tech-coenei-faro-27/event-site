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

  it("diz as datas e os prazos e não promete transferência do bilhete", () => {
    expect(item?.answer).toMatch(/avisamos-te por email/i);
    expect(item?.answer).toMatch(/em até 10 dias úteis depois da aceitação/i);
    expect(item?.answer).toMatch(/até 28 de fevereiro de 2027, inclusive/i);
    expect(item?.answer).toMatch(/conta a data do teu email/i);
    expect(item?.answer).toMatch(/a partir de 1 de março de 2027 não aceitamos pedidos/i);
    expect(item?.answer).not.toMatch(/transfer/i);
  });

  it("os identificadores das perguntas continuam únicos", () => {
    const ids = FAQ_DATA.map((entry) => entry.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
