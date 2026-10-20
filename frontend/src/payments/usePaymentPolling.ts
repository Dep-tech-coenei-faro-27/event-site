import { useEffect, useState } from "react";
import { ApiError } from "../utils/http";
import { getAccount, getTransaction } from "./api";
import { retryAfterSeconds } from "./errors";
import { clearReference } from "./reference";
import { parseServerDate } from "./time";
import type { Account, Transaction } from "./types";

// O ecrã de espera do MB WAY: pergunta ao backend pelo estado do pagamento até ele terminar.
// As regras vêm de docs/api-payments.md:
//  - de 2 em 2 segundos (o backend só pergunta ao MB WAY de 5 em 5, o resto é estado guardado);
//  - com um fluxo de eventos aberto (Server-Sent Events, `GET .../events`) o servidor avisa na hora
//    em que o pagamento muda: cada aviso faz uma consulta imediata e, enquanto o fluxo está vivo,
//    consulta-se só de 10 em 10 segundos (rede de segurança). Se o fluxo falhar ou não existir
//    volta-se aos 2 segundos, por isso o ecrã nunca depende dele;
//  - `pending` depois de `expires_at` NÃO é erro: o lugar continua reservado até o MB WAY dar
//    o pagamento por terminado, por isso é «ainda a confirmar»;
//  - `failed` e `expired` podem ainda passar a pago (callback tardio): antes de dizer «sem
//    cobrança» confere-se a conta (GET /users/me);
//  - pára ao sair da página e pausa com o separador escondido;
//  - uma falha de rede não é o fim: o pagamento não depende do browser, continua a tentar.

export const POLL_INTERVAL_MS = 2000;
/** Consulta de segurança enquanto o fluxo de eventos está vivo. */
export const LIVE_POLL_INTERVAL_MS = 10_000;
const MAX_BACKOFF_MS = 10_000;
/** Falhas seguidas a partir das quais se avisa a pessoa de que se perdeu a ligação. */
const CONNECTION_LOST_AFTER = 3;

export type PaymentPhase =
  | "waiting" // pending, dentro do prazo
  // pending, depois de expires_at: «ainda a confirmar». Conta pelo relógio do browser, por isso
  // um relógio desfasado só troca este rótulo com «waiting»; o estado verdadeiro vem sempre do
  // servidor. O ecrã tem de manter também aqui o aviso «aprova no MB WAY se ainda não aprovaste».
  | "confirming"
  | "confirmed"
  | "failed"
  | "expired"
  | "refund_due"
  | "refunded"
  | "not-found" // referência desconhecida (ou de outra pessoa)
  | "error"; // o servidor recusou a consulta (4xx que não passa a repetir): não insistir

export type PaymentWatch = {
  phase: PaymentPhase;
  transaction: Transaction | null;
  /** A conta, quando se foi ver se um `failed`/`expired` afinal tem bilhete. */
  account: Account | null;
  /** Falhas de rede seguidas: o ecrã pode mostrar «sem ligação, a tentar outra vez». */
  connectionLost: boolean;
  /** `false` em `failed`/`expired` se não se conseguiu ver a conta: não afirmar «sem cobrança». */
  accountChecked: boolean;
};

const INITIAL: PaymentWatch = {
  phase: "waiting",
  transaction: null,
  account: null,
  connectionLost: false,
  accountChecked: true,
};

type Stored = PaymentWatch & { reference: string };

export function usePaymentPolling(
  reference: string | null,
  intervalMs: number = POLL_INTERVAL_MS,
): PaymentWatch {
  const [stored, setStored] = useState<Stored | null>(null);

  useEffect(() => {
    if (!reference) return;
    const ref: string = reference;

    let stopped = false;
    let running = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let failures = 0;
    let live = false; // o fluxo de eventos está aberto
    let refreshAgain = false; // chegou um aviso durante uma consulta
    let source: EventSource | undefined;
    const controller = new AbortController();

    const publish = (watch: PaymentWatch) => {
      if (!stopped) setStored({ ...watch, reference: ref });
    };
    const closeSource = () => {
      source?.close();
      source = undefined;
      live = false;
    };
    const stop = () => {
      stopped = true;
      clearTimeout(timer);
      closeSource();
    };
    const finish = () => {
      stop();
      clearReference(ref);
    };
    const schedule = (ms: number) => {
      if (!stopped) timer = setTimeout(tick, ms);
    };
    const normalDelay = () => (live ? Math.max(LIVE_POLL_INTERVAL_MS, intervalMs) : intervalMs);

    // O servidor avisa quando o pagamento muda: uma consulta já, em vez de esperar pela próxima.
    function openSource() {
      if (typeof EventSource === "undefined" || stopped || source) return;
      try {
        source = new EventSource(`/api/payment/transactions/${encodeURIComponent(ref)}/events`);
      } catch {
        return;
      }
      source.onopen = () => {
        live = true;
        // O servidor envia logo o estado atual (que já faz uma consulta): a seguinte pode ser a lenta.
        if (!stopped && !running) {
          clearTimeout(timer);
          schedule(normalDelay());
        }
      };
      source.addEventListener("status", () => {
        if (stopped) return;
        if (running) {
          refreshAgain = true;
          return;
        }
        clearTimeout(timer);
        schedule(0);
      });
      source.onerror = () => {
        // Sem fluxo (a reconectar ou recusado) volta-se ao ritmo normal de consulta.
        live = false;
        if (source && source.readyState === EventSource.CLOSED) source = undefined;
        if (!stopped && !running) {
          clearTimeout(timer);
          schedule(intervalMs);
        }
      };
    }

    async function tick() {
      if (stopped || running) return;
      if (document.hidden) return; // retoma em visibilitychange
      running = true;
      try {
        const transaction = await getTransaction(ref, { signal: controller.signal });
        if (stopped) return;
        failures = 0;

        if (transaction.status === "pending") {
          const overdue = parseServerDate(transaction.expires_at) < Date.now();
          publish({
            ...INITIAL,
            phase: overdue ? "confirming" : "waiting",
            transaction,
          });
          schedule(normalDelay());
          return;
        }

        if (transaction.status === "failed" || transaction.status === "expired") {
          // Um pagamento tardio pode ter emitido o bilhete: ver a conta antes de dar o fim.
          try {
            const account = await getAccount({ signal: controller.signal });
            if (stopped) return;
            const phase = account.ticket
              ? "confirmed"
              : account.refund_due
                ? "refund_due"
                : transaction.status;
            publish({ phase, transaction, account, connectionLost: false, accountChecked: true });
          } catch {
            if (stopped) return;
            publish({
              phase: transaction.status,
              transaction,
              account: null,
              connectionLost: false,
              accountChecked: false,
            });
          }
          finish();
          return;
        }

        // confirmed, refund_due, refunded
        publish({ ...INITIAL, phase: transaction.status, transaction });
        finish();
      } catch (error) {
        if (stopped) return; // o abort ao sair chega aqui como erro de rede
        if (error instanceof ApiError) {
          if (error.status === 404) {
            publish({ ...INITIAL, phase: "not-found" });
            finish();
            return;
          }
          if (error.status === 401) {
            // O http() já levou a pessoa ao login. A referência fica guardada: depois de entrar
            // outra vez o ecrã de espera retoma este pagamento.
            stop();
            return;
          }
          if (error.status === 429) {
            // Respeitar o servidor: nunca antes do que ele pediu.
            schedule(Math.max(retryAfterSeconds(error.retryAfter) * 1000, normalDelay()));
            return;
          }
          if (error.status >= 400 && error.status < 500 && error.status !== 408) {
            // Um 403 ou 4xx não passa com o tempo: insistir só esconderia o problema.
            publish({ ...INITIAL, phase: "error" });
            stop();
            return;
          }
        }
        // Rede em baixo ou 5xx: o pagamento segue no MB WAY. Tentar outra vez, cada vez mais devagar.
        failures += 1;
        setStored((current) =>
          current && current.reference === ref
            ? { ...current, connectionLost: failures >= CONNECTION_LOST_AFTER }
            : { ...INITIAL, reference: ref, connectionLost: failures >= CONNECTION_LOST_AFTER },
        );
        schedule(Math.min(intervalMs * 2 ** failures, MAX_BACKOFF_MS));
      } finally {
        running = false;
        if (refreshAgain && !stopped) {
          refreshAgain = false;
          clearTimeout(timer);
          schedule(0);
        }
      }
    }

    const onVisibility = () => {
      if (document.hidden || stopped) return;
      clearTimeout(timer);
      schedule(0);
    };
    document.addEventListener("visibilitychange", onVisibility);
    schedule(0);
    openSource();

    return () => {
      stopped = true;
      clearTimeout(timer);
      closeSource();
      controller.abort();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [reference, intervalMs]);

  return stored && stored.reference === reference ? stored : INITIAL;
}
