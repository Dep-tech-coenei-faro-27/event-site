import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, NetworkError } from "../utils/http";
import * as api from "./api";
import { saveReference, loadReference } from "./reference";
import type { Account, Transaction } from "./types";
import { POLL_INTERVAL_MS, usePaymentPolling } from "./usePaymentPolling";

vi.mock("./api");

const REF = "ENEI-TEST000001";
const future = () => new Date(Date.now() + 240_000).toISOString();
const past = () => new Date(Date.now() - 60_000).toISOString();

const tx = (over: Partial<Transaction> = {}): Transaction => ({
  reference: REF,
  ticket_tier: "geral",
  status: "pending",
  amount_cents: 5000,
  quantity: 1,
  currency: "EUR",
  phone: "912345678",
  expires_at: future(),
  confirmed_at: null,
  created_at: new Date().toISOString(),
  ...over,
});

const account = (over: Partial<Account> = {}): Account => ({
  qr_code: null,
  ticket: null,
  pending_payment: null,
  refund_due: null,
  ...over,
});

const getTransaction = vi.mocked(api.getTransaction);
const getAccount = vi.mocked(api.getAccount);

let hidden = false;
const setHidden = (value: boolean) => {
  hidden = value;
  document.dispatchEvent(new Event("visibilitychange"));
};

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  hidden = false;
  Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
  getTransaction.mockReset();
  getAccount.mockReset();
  sessionStorage.clear();
});

afterEach(() => {
  cleanup(); // sem `globals` o testing-library não desmonta sozinho
  vi.useRealTimers();
});

describe("usePaymentPolling", () => {
  it("não faz nada sem referência", async () => {
    const { result } = renderHook(() => usePaymentPolling(null));
    await advance(10_000);
    expect(getTransaction).not.toHaveBeenCalled();
    expect(result.current.phase).toBe("waiting");
  });

  it("pergunta logo e depois de 2 em 2 segundos enquanto está pending", async () => {
    getTransaction.mockResolvedValue(tx());
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    expect(result.current.phase).toBe("waiting");
    await advance(POLL_INTERVAL_MS);
    expect(getTransaction).toHaveBeenCalledTimes(2);
    await advance(POLL_INTERVAL_MS * 3);
    expect(getTransaction).toHaveBeenCalledTimes(5);
  });

  it("pending depois de expires_at é «ainda a confirmar», não erro, e continua a perguntar", async () => {
    getTransaction.mockResolvedValue(tx({ expires_at: past() }));
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(result.current.phase).toBe("confirming");
    await advance(POLL_INTERVAL_MS * 2);
    expect(getTransaction).toHaveBeenCalledTimes(3);
    expect(result.current.phase).toBe("confirming");
  });

  it("confirmed: pára de perguntar e apaga a referência guardada", async () => {
    saveReference(REF);
    getTransaction.mockResolvedValueOnce(tx()).mockResolvedValue(tx({ status: "confirmed" }));
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    await advance(POLL_INTERVAL_MS);
    expect(result.current.phase).toBe("confirmed");
    expect(loadReference()).toBeNull();
    const calls = getTransaction.mock.calls.length;
    await advance(POLL_INTERVAL_MS * 5);
    expect(getTransaction).toHaveBeenCalledTimes(calls);
    expect(getAccount).not.toHaveBeenCalled();
  });

  it.each(["refund_due", "refunded"] as const)("%s é final e pára", async (status) => {
    getTransaction.mockResolvedValue(tx({ status }));
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(result.current.phase).toBe(status);
    await advance(POLL_INTERVAL_MS * 3);
    expect(getTransaction).toHaveBeenCalledTimes(1);
  });

  it.each(["expired", "failed"] as const)(
    "%s sem bilhete na conta: é mesmo o fim, e a conta foi vista uma só vez",
    async (status) => {
      getTransaction.mockResolvedValue(tx({ status }));
      getAccount.mockResolvedValue(account());
      const { result } = renderHook(() => usePaymentPolling(REF));
      await advance(0);
      expect(result.current).toMatchObject({ phase: status, accountChecked: true });
      await advance(POLL_INTERVAL_MS * 3);
      expect(getAccount).toHaveBeenCalledTimes(1);
      expect(getTransaction).toHaveBeenCalledTimes(1);
    },
  );

  it.each(["expired", "failed"] as const)(
    "%s mas a conta já tem bilhete (pagamento tardio): mostra confirmado",
    async (status) => {
      getTransaction.mockResolvedValue(tx({ status }));
      getAccount.mockResolvedValue(
        account({
          qr_code: "ENEI27.1.x.y",
          ticket: {
            reference: "T1",
            tier: "geral",
            tier_name: "Passe geral",
            holder_name: "Ana",
            paid_at: null,
          },
        }),
      );
      const { result } = renderHook(() => usePaymentPolling(REF));
      await advance(0);
      expect(result.current.phase).toBe("confirmed");
      expect(result.current.account?.ticket?.tier_name).toBe("Passe geral");
    },
  );

  it("expired mas a conta tem reembolso a caminho: mostra refund_due", async () => {
    getTransaction.mockResolvedValue(tx({ status: "expired" }));
    getAccount.mockResolvedValue(account({ refund_due: { reference: REF, amount_cents: 5000 } }));
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(result.current.phase).toBe("refund_due");
  });

  it("expired sem conseguir ver a conta: não afirma que não houve cobrança", async () => {
    getTransaction.mockResolvedValue(tx({ status: "expired" }));
    getAccount.mockRejectedValue(new NetworkError());
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(result.current).toMatchObject({ phase: "expired", accountChecked: false });
  });

  it("404: referência desconhecida, pára e limpa", async () => {
    saveReference(REF);
    getTransaction.mockRejectedValue(new ApiError(404, "Not found", "Not found"));
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(result.current.phase).toBe("not-found");
    expect(loadReference()).toBeNull();
    await advance(POLL_INTERVAL_MS * 3);
    expect(getTransaction).toHaveBeenCalledTimes(1);
  });

  it("401: pára e GUARDA a referência, para retomar depois de entrar outra vez", async () => {
    saveReference(REF);
    getTransaction.mockRejectedValue(new ApiError(401, "x", "Invalid or expired token"));
    renderHook(() => usePaymentPolling(REF));
    await advance(0);
    await advance(POLL_INTERVAL_MS * 3);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    expect(loadReference()).toBe(REF);
  });

  it.each([400, 403, 422])("%i: o servidor recusou, não insiste nem finge perda de ligação", async (status) => {
    getTransaction.mockRejectedValue(new ApiError(status, "x", "recusado"));
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    await advance(POLL_INTERVAL_MS * 10);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    expect(result.current).toMatchObject({ phase: "error", connectionLost: false });
  });

  it("um final de outro pagamento não apaga a referência do pagamento novo", async () => {
    saveReference("ENEI-NOVA00000");
    getTransaction.mockResolvedValue(tx({ status: "confirmed" }));
    renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(loadReference()).toBe("ENEI-NOVA00000");
  });

  it("em StrictMode (monta, desmonta, monta) só fica um relógio a correr", async () => {
    getTransaction.mockResolvedValue(tx());
    renderHook(() => usePaymentPolling(REF), { reactStrictMode: true });
    await advance(0);
    const afterStart = getTransaction.mock.calls.length;
    await advance(POLL_INTERVAL_MS * 3);
    expect(getTransaction.mock.calls.length - afterStart).toBe(3);
  });

  it("429: espera pelo menos o Retry-After antes de voltar a perguntar", async () => {
    getTransaction
      .mockRejectedValueOnce(new ApiError(429, "x", "Too many", "7"))
      .mockResolvedValue(tx());
    renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    await advance(6_900);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    await advance(200);
    expect(getTransaction).toHaveBeenCalledTimes(2);
  });

  it("429 sem Retry-After usa pelo menos o intervalo normal", async () => {
    getTransaction.mockRejectedValueOnce(new ApiError(429, "x", "Too many")).mockResolvedValue(tx());
    renderHook(() => usePaymentPolling(REF));
    await advance(0);
    await advance(POLL_INTERVAL_MS - 100);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    await advance(200);
    expect(getTransaction).toHaveBeenCalledTimes(2);
  });

  it("sem rede: continua a tentar, cada vez mais devagar, e avisa à 3.ª falha seguida", async () => {
    getTransaction.mockRejectedValue(new NetworkError());
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0); // falha 1 -> 4 s
    expect(result.current.connectionLost).toBe(false);
    await advance(4_000); // falha 2 -> 8 s
    expect(result.current.connectionLost).toBe(false);
    await advance(8_000); // falha 3 -> 10 s (teto)
    expect(result.current.connectionLost).toBe(true);
    expect(getTransaction).toHaveBeenCalledTimes(3);
    await advance(10_000);
    expect(getTransaction).toHaveBeenCalledTimes(4);
    await advance(10_000);
    expect(getTransaction).toHaveBeenCalledTimes(5);
  });

  it("um 500 trata-se como falha de ligação e recupera quando volta", async () => {
    getTransaction
      .mockRejectedValueOnce(new ApiError(500, "x", "boom"))
      .mockRejectedValueOnce(new ApiError(500, "x", "boom"))
      .mockRejectedValueOnce(new ApiError(500, "x", "boom"))
      .mockResolvedValue(tx());
    const { result } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    await advance(4_000);
    await advance(8_000);
    expect(result.current.connectionLost).toBe(true);
    await advance(10_000);
    expect(result.current).toMatchObject({ phase: "waiting", connectionLost: false });
  });

  describe("o relógio do browser e o prazo", () => {
    const MIN = 60_000;
    // Hora do servidor = hora do browser + skew. O prazo (`expires_at`) é sempre hora do servidor.
    const serverClock = (skewMs: number) => () => new Date(Date.now() + skewMs);

    it("data sem fuso (SQLite, UTC) não desloca o prazo: dentro do prazo é «waiting»", async () => {
      const naive = new Date(Date.now() + 240_000).toISOString().replace("Z", "");
      getTransaction.mockResolvedValue(tx({ expires_at: naive }));
      const { result } = renderHook(() => usePaymentPolling(REF));
      await advance(0);
      expect(result.current.phase).toBe("waiting");
    });

    it("data com fuso diferente do UTC dá o mesmo resultado", async () => {
      const plusOne = new Date(Date.now() + 240_000 + 3_600_000).toISOString().replace("Z", "+01:00");
      getTransaction.mockResolvedValue(tx({ expires_at: plusOne }));
      const { result } = renderHook(() => usePaymentPolling(REF));
      await advance(0);
      expect(result.current.phase).toBe("waiting");
    });

    it("relógio do browser ADIANTADO: só o rótulo muda («confirming»); continua a perguntar e o estado final vem do servidor", async () => {
      const server = serverClock(-10 * MIN); // browser 10 min à frente do servidor
      getTransaction
        .mockResolvedValueOnce(tx({ expires_at: new Date(server().getTime() + 200_000).toISOString() }))
        .mockResolvedValueOnce(tx({ expires_at: new Date(server().getTime() + 200_000).toISOString() }))
        .mockResolvedValue(tx({ status: "confirmed" }));
      const { result } = renderHook(() => usePaymentPolling(REF));
      await advance(0);
      expect(result.current.phase).toBe("confirming"); // rótulo errado, mas inofensivo
      await advance(POLL_INTERVAL_MS);
      expect(result.current.phase).toBe("confirming");
      expect(getTransaction).toHaveBeenCalledTimes(2); // não parou
      await advance(POLL_INTERVAL_MS);
      expect(result.current.phase).toBe("confirmed"); // o servidor manda
    });

    it("relógio do browser ATRASADO: continua «waiting» depois do prazo, mas o servidor dá o fim e o hook pára", async () => {
      const server = serverClock(10 * MIN); // browser 10 min atrás do servidor
      const overdueOnServer = new Date(server().getTime() - 60_000).toISOString();
      getTransaction
        .mockResolvedValueOnce(tx({ expires_at: overdueOnServer }))
        .mockResolvedValue(tx({ status: "expired", expires_at: overdueOnServer }));
      getAccount.mockResolvedValue(account());
      const { result } = renderHook(() => usePaymentPolling(REF));
      await advance(0);
      expect(result.current.phase).toBe("waiting");
      await advance(POLL_INTERVAL_MS);
      expect(result.current.phase).toBe("expired");
      await advance(POLL_INTERVAL_MS * 5);
      expect(getTransaction).toHaveBeenCalledTimes(2);
    });

    it("uma data ilegível não rebenta nem para o polling: fica «waiting»", async () => {
      getTransaction.mockResolvedValue(tx({ expires_at: "amanhã" }));
      const { result } = renderHook(() => usePaymentPolling(REF));
      await advance(0);
      await advance(POLL_INTERVAL_MS * 2);
      expect(result.current.phase).toBe("waiting");
      expect(getTransaction).toHaveBeenCalledTimes(3);
    });
  });

  it("nunca tem dois pedidos ao mesmo tempo, mesmo que o servidor demore", async () => {
    let release: (t: Transaction) => void = () => {};
    getTransaction.mockImplementation(
      () =>
        new Promise<Transaction>((resolve) => {
          release = resolve;
        }),
    );
    renderHook(() => usePaymentPolling(REF));
    await advance(0);
    await advance(POLL_INTERVAL_MS * 5);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    await act(async () => release(tx()));
    await advance(POLL_INTERVAL_MS);
    expect(getTransaction).toHaveBeenCalledTimes(2);
  });

  it("voltar ao separador a meio de um pedido não abre um segundo pedido", async () => {
    let release: (t: Transaction) => void = () => {};
    getTransaction.mockImplementation(
      () =>
        new Promise<Transaction>((resolve) => {
          release = resolve;
        }),
    );
    renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    act(() => setHidden(false)); // visibilitychange com o pedido ainda por responder
    await advance(0);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    await act(async () => release(tx()));
    await advance(POLL_INTERVAL_MS);
    expect(getTransaction).toHaveBeenCalledTimes(2);
  });

  it("ao sair da página pára e cancela o pedido em curso", async () => {
    let signal: AbortSignal | undefined;
    getTransaction.mockImplementation((_ref, options) => {
      signal = options?.signal as AbortSignal;
      return Promise.resolve(tx());
    });
    const { unmount } = renderHook(() => usePaymentPolling(REF));
    await advance(0);
    unmount();
    expect(signal?.aborted).toBe(true);
    await advance(POLL_INTERVAL_MS * 5);
    expect(getTransaction).toHaveBeenCalledTimes(1);
  });

  it("com o separador escondido não pergunta; ao voltar pergunta logo", async () => {
    getTransaction.mockResolvedValue(tx());
    renderHook(() => usePaymentPolling(REF));
    await advance(0);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    hidden = true;
    await advance(POLL_INTERVAL_MS * 5);
    expect(getTransaction).toHaveBeenCalledTimes(1); // o agendado vê que está escondido e para
    await advance(POLL_INTERVAL_MS * 5);
    expect(getTransaction).toHaveBeenCalledTimes(1);
    act(() => setHidden(false));
    await advance(0);
    expect(getTransaction).toHaveBeenCalledTimes(2);
    await advance(POLL_INTERVAL_MS);
    expect(getTransaction).toHaveBeenCalledTimes(3);
  });

  it("começar com o separador escondido também espera", async () => {
    hidden = true;
    getTransaction.mockResolvedValue(tx());
    renderHook(() => usePaymentPolling(REF));
    await advance(POLL_INTERVAL_MS * 3);
    expect(getTransaction).not.toHaveBeenCalled();
    act(() => setHidden(false));
    await advance(0);
    expect(getTransaction).toHaveBeenCalledTimes(1);
  });

  it("ao mudar de referência não herda o estado da anterior", async () => {
    getTransaction.mockImplementation((reference) =>
      Promise.resolve(
        reference === REF ? tx({ status: "confirmed" }) : tx({ reference: "ENEI-OUTRA00001" }),
      ),
    );
    const { result, rerender } = renderHook(({ r }) => usePaymentPolling(r), {
      initialProps: { r: REF as string | null },
    });
    await advance(0);
    expect(result.current.phase).toBe("confirmed");
    rerender({ r: "ENEI-OUTRA00001" });
    expect(result.current.phase).toBe("waiting");
    expect(result.current.transaction).toBeNull();
    await advance(0);
    expect(result.current.transaction?.reference).toBe("ENEI-OUTRA00001");
  });
});
