import { afterEach, describe, expect, it, vi } from "vitest";
import { getAccount, getTiers, getTransaction, initiatePayment } from "./api";

function stubFetch(body: unknown = {}, status = 200) {
  const fetchMock = vi.fn<typeof fetch>(() =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("cliente de /payment", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("GET /payment/tiers", async () => {
    const f = stubFetch([{ tier: "geral" }]);
    await expect(getTiers()).resolves.toEqual([{ tier: "geral" }]);
    expect(f).toHaveBeenCalledWith("/api/payment/tiers", expect.objectContaining({ credentials: "include" }));
  });

  it("POST /payment/initiate só envia a modalidade e o telemóvel, nunca preço nem quantidade", async () => {
    const f = stubFetch({ reference: "ENEI-1" }, 201);
    await initiatePayment({ ticket_tier: "geral", phone: "912 345 678" });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("/api/payment/initiate");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({ ticket_tier: "geral", phone: "912 345 678" });
  });

  it("GET /payment/transactions/{reference} escapa a referência", async () => {
    const f = stubFetch({ status: "pending" });
    await getTransaction("ENEI-AB/12");
    expect(f.mock.calls[0][0]).toBe("/api/payment/transactions/ENEI-AB%2F12");
  });

  it("GET /users/me", async () => {
    const f = stubFetch({ qr_code: null, ticket: null, pending_payment: null, refund_due: null });
    await expect(getAccount()).resolves.toMatchObject({ ticket: null });
    expect(f.mock.calls[0][0]).toBe("/api/users/me");
  });
});
