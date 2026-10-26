import { describe, expect, it } from "vitest";
import { ApiError, NetworkError } from "../utils/http";
import { describeInitiateError, retryAfterSeconds } from "./errors";

const api = (status: number, detail: unknown, retryAfter: string | null = null) =>
  new ApiError(status, typeof detail === "string" ? detail : `HTTP ${status}`, detail, retryAfter);

describe("describeInitiateError (uma linha por erro de docs/api-payments.md)", () => {
  it("401: sessão terminada, levar ao login", () => {
    const f = describeInitiateError(api(401, "Not authenticated"));
    expect(f).toMatchObject({ kind: "session-ended", action: "login" });
  });

  it("403 email por verificar: oferecer reenviar a verificação", () => {
    const f = describeInitiateError(api(403, "Please verify your email address to continue."));
    expect(f).toMatchObject({ kind: "email-unverified", action: "resend-verification" });
  });

  it("403 estudante sem verificação: levar ao comprovativo ou a outra modalidade", () => {
    const f = describeInitiateError(api(403, "Student verification is required to buy this ticket"));
    expect(f).toMatchObject({ kind: "student-required", action: "send-student-proof" });
    expect(f.message).toMatch(/comprovativo/);
  });

  it("409 esgotado e 409 já tem bilhete são casos diferentes (nunca dizer «esgotado» a quem já tem)", () => {
    const soldOut = describeInitiateError(api(409, "This ticket tier is sold out"));
    const mine = describeInitiateError(
      api(409, "You already have a ticket or a payment in progress"),
    );
    expect(soldOut).toMatchObject({ kind: "sold-out", action: "choose-another-tier" });
    expect(mine).toMatchObject({ kind: "already-in-progress", action: "view-account" });
    expect(mine.message).not.toMatch(/esgot/i);
  });

  it("422 do telemóvel aponta o campo", () => {
    const f = describeInitiateError(
      api(422, [{ type: "value_error", loc: ["body", "phone"], msg: "invalid" }]),
    );
    expect(f).toMatchObject({ kind: "invalid-input", field: "phone", action: "fix-field" });
  });

  it("422 do NIF aponta o campo", () => {
    const f = describeInitiateError(
      api(422, [{ type: "value_error", loc: ["body", "nif"], msg: "nif check digit is not valid" }]),
    );
    expect(f).toMatchObject({ kind: "invalid-input", field: "nif", action: "fix-field" });
    expect(f.message).toMatch(/NIF/);
  });

  it("422 de modalidade desconhecida manda escolher outra", () => {
    const f = describeInitiateError(
      api(422, [{ type: "enum", loc: ["body", "ticket_tier"], msg: "x" }]),
    );
    expect(f).toMatchObject({ kind: "invalid-input", field: "ticket_tier" });
  });

  it("422 sem campo conhecido não deixa o utilizador sem mensagem", () => {
    const f = describeInitiateError(api(422, [{ loc: ["body", "outro"] }]));
    expect(f.kind).toBe("invalid-input");
    expect(f.message).not.toBe("");
  });

  it("429 usa o Retry-After do servidor", () => {
    const f = describeInitiateError(api(429, "Too many requests", "12"));
    expect(f).toMatchObject({ kind: "rate-limited", action: "wait-and-retry", retryAfterSeconds: 12 });
    expect(f.message).toContain("12 segundos");
  });

  it("429 sem Retry-After continua a dar uma mensagem e 0 segundos", () => {
    const f = describeInitiateError(api(429, "Too many requests"));
    expect(f.retryAfterSeconds).toBe(0);
    expect(f.message).toContain("Tenta novamente");
  });

  it("502: deixa tentar logo, a transação falhada não conta como pagamento em curso", () => {
    const f = describeInitiateError(
      api(502, "Payment could not be initiated. Please try again."),
    );
    expect(f).toMatchObject({ kind: "gateway-failed", action: "retry" });
  });

  it("503: bilheteira fechada e pagamentos desligados, sem repetição", () => {
    expect(describeInitiateError(api(503, "Ticket sales are not open yet"))).toMatchObject({
      kind: "sales-closed",
      action: "none",
    });
    expect(describeInitiateError(api(503, "Payments are currently disabled."))).toMatchObject({
      kind: "payments-off",
      action: "none",
    });
  });

  it("rede ou 5xx: «sem ligação» e nunca repetir sozinho", () => {
    for (const e of [new NetworkError(), api(500, "boom"), api(504, "timeout")]) {
      expect(describeInitiateError(e)).toMatchObject({ kind: "no-connection", action: "retry" });
    }
  });

  it("um código ou texto que não conhecemos cai em «unknown», sem rebentar", () => {
    expect(describeInitiateError(api(409, "outra coisa"))).toMatchObject({ kind: "unknown" });
    expect(describeInitiateError(api(403, "outra coisa"))).toMatchObject({ kind: "unknown" });
    expect(describeInitiateError(api(418, "chá"))).toMatchObject({ kind: "unknown" });
    expect(describeInitiateError(new Error("x"))).toMatchObject({ kind: "unknown" });
    expect(describeInitiateError(undefined)).toMatchObject({ kind: "unknown" });
  });

  it("todas as mensagens estão em português e nenhuma é o texto inglês da API", () => {
    const cases = [
      api(401, "Not authenticated"),
      api(403, "Please verify your email address to continue."),
      api(409, "This ticket tier is sold out"),
      api(502, "Payment could not be initiated. Please try again."),
      api(503, "Payments are currently disabled."),
    ];
    for (const c of cases) {
      expect(describeInitiateError(c).message).not.toBe(c.message);
    }
  });
});

describe("retryAfterSeconds", () => {
  it("lê segundos, datas HTTP e valores inválidos", () => {
    expect(retryAfterSeconds("7")).toBe(7);
    expect(retryAfterSeconds("0")).toBe(0);
    expect(retryAfterSeconds("-3")).toBe(0);
    expect(retryAfterSeconds(null)).toBe(0);
    expect(retryAfterSeconds("lixo")).toBe(0);
    const inTenSeconds = new Date(Date.now() + 10_000).toUTCString();
    expect(retryAfterSeconds(inTenSeconds)).toBeGreaterThanOrEqual(9);
  });
});
