import { describe, expect, it } from "vitest";
import { formatOpeningTime, formatPrice, isPortuguesePhone, normalizePhone } from "./format";

describe("formatPrice", () => {
  it("escreve cêntimos em euros, ao modo português", () => {
    expect(formatPrice(5000)).toMatch(/50,00\s?€/);
    expect(formatPrice(2550)).toMatch(/25,50\s?€/);
  });
  it("uma modalidade sem preço diz «A confirmar»", () => {
    expect(formatPrice(null)).toBe("A confirmar");
  });
});

describe("telemóvel português", () => {
  it.each([
    ["912 345 678", "912345678"],
    ["+351 912 345 678", "912345678"],
    ["00351912345678", "912345678"],
    ["912-345-678", "912345678"],
  ])("normaliza %s", (raw, expected) => {
    expect(normalizePhone(raw)).toBe(expected);
    expect(isPortuguesePhone(raw)).toBe(true);
  });
  it.each(["", "12345", "812345678", "9123456789", "+44 7911 123456"])("recusa %s", (raw) => {
    expect(isPortuguesePhone(raw)).toBe(false);
  });
});

describe("formatOpeningTime", () => {
  it("escreve a hora de Lisboa em português", () => {
    // em novembro Lisboa está a UTC+0; em julho, a UTC+1
    expect(formatOpeningTime("2026-11-02T09:00:00+00:00")).toBe("2 de novembro às 09:00");
    expect(formatOpeningTime("2026-07-02T09:00:00+00:00")).toBe("2 de julho às 10:00");
  });

  it("uma data inválida dá texto vazio (a página usa a frase sem data)", () => {
    expect(formatOpeningTime("amanhã")).toBe("");
  });
});
