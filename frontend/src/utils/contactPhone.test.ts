import { describe, expect, it } from "vitest";
import { isContactPhone, normalizeContactPhone } from "./contactPhone";

describe("número de contacto", () => {
  it.each([
    ["912345678", "912345678"],
    ["912 345 678", "912345678"],
    ["+351 912-345.678", "+351912345678"],
    ["(+351) 912 345 678", "+351912345678"],
    ["00351 912 345 678", "+351912345678"],
  ])("normaliza %s", (input, expected) => {
    expect(normalizeContactPhone(input)).toBe(expected);
    expect(isContactPhone(input)).toBe(true);
  });

  it.each(["12345", "abcdefghi", "912 345 67x", "+1234567890123456", "+", "++351912345678"])("recusa %s", (input) => {
    expect(isContactPhone(input)).toBe(false);
  });

  it("aceita estrangeiros (não é só telemóvel português)", () => {
    expect(isContactPhone("+44 7700 900123")).toBe(true);
  });
});
