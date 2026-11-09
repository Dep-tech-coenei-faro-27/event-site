import { ApiError, NetworkError, http } from "./http";
import { retryAfterMessage } from "./RetryAfter";

/**
 * O estado de estudante em `GET /users/me` (docs/api-auth.md). `pending` é o nome antigo de
 * `none`: contas e código anteriores ao comprovativo ainda o podem devolver.
 */
export type StudentVerificationStatus = "none" | "submitted" | "verified" | "rejected" | "pending";

export type StudentStatus = Exclude<StudentVerificationStatus, "pending">;

/** O estado sem o nome antigo; um valor em falta ou desconhecido conta como «nunca enviou». */
export function studentStatus(raw: string | null | undefined): StudentStatus {
  return raw === "submitted" || raw === "verified" || raw === "rejected" ? raw : "none";
}

/** O mesmo limite do servidor (`STUDENT_PROOF_MAX_BYTES`). */
export const STUDENT_PROOF_MAX_BYTES = 1_048_576;

/** Para o `accept` do campo: só ajuda a escolher, o servidor vê o tipo pelos primeiros bytes. */
export const STUDENT_PROOF_ACCEPT = ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";

const ALLOWED_EXTENSION = /\.(pdf|jpe?g|png)$/i;

export const ORGANIZATION_EMAIL = "geral@eneiconf.pt";

/** O que a pessoa precisa para o comprovativo ser aceite (as regras do backend, #218). */
export const STUDENT_PROOF_RULES = [
  "Comprovativo de matrícula do ano letivo 2026/2027.",
  "Com o teu nome igual ao da conta.",
  "De preferência o PDF original, com a assinatura digital da instituição (sem o imprimir nem digitalizar).",
] as const;

/** Erro a mostrar antes de enviar (tamanho e tipo), ou `null` se o ficheiro pode seguir. */
export function studentProofFileError(file: File | null): string | null {
  if (!file) return "Escolhe o ficheiro do comprovativo.";
  if (file.size === 0) return "O ficheiro está vazio.";
  if (file.size > STUDENT_PROOF_MAX_BYTES) return "O ficheiro tem mais de 1 MB.";
  if (!ALLOWED_EXTENSION.test(file.name)) return "Só aceitamos PDF, JPG ou PNG.";
  return null;
}

/** `POST /users/me/student-proof`: devolve o estado em que a conta ficou. */
export function sendStudentProof(file: File, options?: Parameters<typeof http>[1]) {
  const form = new FormData();
  form.append("file", file);
  return http<{ status: StudentVerificationStatus }>("/users/me/student-proof", {
    ...options,
    method: "POST",
    body: form,
  });
}

export type StudentProofFailure = {
  message: string;
  /** 401: a sessão acabou, leva ao login. */
  sessionEnded?: boolean;
  /** 409: o estado mudou noutro lado (já verificado ou já há um à espera); recarregar a conta. */
  stale?: boolean;
};

const ALREADY_VERIFIED = "The account is already a verified student";

/** O que dizer quando o envio falha. Os `detail` da API são em inglês: aqui o texto é nosso. */
export function studentProofError(error: unknown): StudentProofFailure {
  if (error instanceof NetworkError) {
    return { message: "Sem ligação. Verifica a rede e tenta outra vez." };
  }
  if (!(error instanceof ApiError)) return { message: "Algo correu mal. Tenta outra vez." };

  switch (error.status) {
    case 401:
      return { message: "A tua sessão terminou. Entra outra vez para enviar.", sessionEnded: true };
    case 403:
      return { message: "Confirma o teu email antes de enviares o comprovativo." };
    case 409:
      return error.detail === ALREADY_VERIFIED
        ? { message: "A tua conta já está verificada como estudante.", stale: true }
        : { message: "Já tens um comprovativo à espera de revisão.", stale: true };
    case 413:
      return { message: "O ficheiro tem mais de 1 MB." };
    case 415:
      return { message: "Só aceitamos PDF, JPG ou PNG." };
    case 422:
      return { message: "O ficheiro está vazio ou não chegou. Escolhe-o outra vez." };
    case 429:
      return { message: retryAfterMessage(error.retryAfter, "Enviaste demasiados comprovativos.") };
    default:
      return { message: "O servidor não conseguiu receber o comprovativo. Tenta outra vez daqui a pouco." };
  }
}
