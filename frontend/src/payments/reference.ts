// A referência do pagamento em curso fica no sessionStorage logo que o POST /payment/initiate
// responde, para o ecrã de espera conseguir retomar se a pessoa recarregar a página. O
// armazenamento pode estar bloqueado (janela privada, definições): nunca pode partir o fluxo.

const KEY = "enei.payment.reference";

export function saveReference(reference: string): void {
  try {
    sessionStorage.setItem(KEY, reference);
  } catch {
    // sem armazenamento: o ecrã de espera usa a referência que já tem em memória
  }
}

export function loadReference(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

/** Apaga a referência guardada; com `only`, só se for essa (não apaga a de um pagamento mais novo). */
export function clearReference(only?: string): void {
  try {
    if (only !== undefined && sessionStorage.getItem(KEY) !== only) return;
    sessionStorage.removeItem(KEY);
  } catch {
    // ignorar
  }
}
