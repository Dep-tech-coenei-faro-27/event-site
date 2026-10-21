import { describe, expect, it } from "vitest";
import { formatPrice, isPortuguesePhone, normalizePhone } from "./format";

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
