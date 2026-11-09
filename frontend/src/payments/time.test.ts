import { afterEach, describe, expect, it, vi } from "vitest";
import { parseServerDate } from "./time";

describe("parseServerDate", () => {
  afterEach(() => vi.restoreAllMocks());

  it("lê o mesmo instante com fuso, em Z e sem fuso (UTC)", () => {
    const instant = Date.UTC(2026, 9, 17, 0, 35, 36, 595);
    expect(parseServerDate("2026-10-17T00:35:36.595572")).toBe(instant); // SQLite, sem fuso
    expect(parseServerDate("2026-10-17T00:35:36.595572Z")).toBe(instant);
    expect(parseServerDate("2026-10-17T01:35:36.595572+01:00")).toBe(instant); // Postgres
    expect(parseServerDate("2026-10-16T22:35:36.595572-02:00")).toBe(instant);
    expect(parseServerDate("2026-10-17T00:35:36+0000")).toBe(Date.UTC(2026, 9, 17, 0, 35, 36));
  });

  it("não depende do fuso do browser: uma data sem fuso nunca é hora local", () => {
    const plain = "2026-10-17T00:35:36";
    expect(parseServerDate(plain)).toBe(Date.parse(`${plain}Z`));
  });

  it("uma data sem fuso chega ao Date.parse já marcada como UTC (protege o CI, que corre em UTC)", () => {
    const parse = vi.spyOn(Date, "parse");
    parseServerDate("2026-10-17T00:35:36.595572");
    parseServerDate("2026-10-17T01:35:36+01:00");
    parseServerDate("2026-10-17T00:35:36Z");
    expect(parse.mock.calls.map(([text]) => text)).toEqual([
      "2026-10-17T00:35:36.595572Z", // acrescentou o Z
      "2026-10-17T01:35:36+01:00", // já tinha fuso: intacta
      "2026-10-17T00:35:36Z",
    ]);
    parse.mockRestore();
  });

  it("devolve NaN para o que não é data", () => {
    expect(Number.isNaN(parseServerDate("amanhã"))).toBe(true);
    expect(Number.isNaN(parseServerDate(""))).toBe(true);
  });
});
