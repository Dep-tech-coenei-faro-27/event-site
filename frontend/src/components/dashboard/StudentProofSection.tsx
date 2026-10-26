import { useId, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import AccountPanel from "./AccountPanel";
import {
  ORGANIZATION_EMAIL,
  STUDENT_PROOF_ACCEPT,
  STUDENT_PROOF_RULES,
  sendStudentProof,
  studentProofError,
  studentProofFileError,
  studentStatus,
  type StudentStatus,
  type StudentVerificationStatus,
} from "../../utils/studentProof";

interface StudentProofSectionProps {
  /** `student_verification_status` de `GET /users/me`. */
  status: StudentVerificationStatus | undefined;
  /** O estado mudou (envio aceite ou recebido). */
  onStatusChange: (status: StudentVerificationStatus) => void;
  /** O servidor diz que o estado já não é o que se mostra (409): volta a ler a conta. */
  onStale: () => void;
}

const BADGE: Record<StudentStatus, { label: string; className: string } | null> = {
  none: null,
  submitted: { label: "Em revisão", className: "border-areia/45 bg-areia/10 text-areia" },
  verified: { label: "Verificado", className: "border-[#10b981]/35 bg-[#10b981]/10 text-[#10b981]" },
  rejected: { label: "Recusado", className: "border-coral-vivo/45 bg-coral-vivo/10 text-coral-vivo" },
};

/**
 * «Comprovativo de estudante» (#271): quem não tem email de aluno envia o comprovativo de matrícula,
 * vê o estado e, se for recusado, porquê e o que fazer. A API não diz o motivo concreto da recusa:
 * mostram-se as regras de aceitação e o contacto da organização.
 */
export default function StudentProofSection({ status, onStatusChange, onStale }: StudentProofSectionProps) {
  const current = studentStatus(status);
  const badge = BADGE[current];
  // O formulário desaparece depois do envio: o resultado é anunciado aqui.
  const [notice, setNotice] = useState("");

  const onSent = (next: StudentVerificationStatus) => {
    setNotice(
      studentStatus(next) === "verified"
        ? "Comprovativo aceite. A tua conta já é de estudante."
        : "Comprovativo enviado. Vamos revê-lo e o resultado aparece aqui.",
    );
    onStatusChange(next);
  };

  return (
    <AccountPanel
      id="comprovativo"
      eyebrow="PREÇO DE ESTUDANTE"
      title="Comprovativo de estudante"
      description="Sem email de aluno, envia o comprovativo de matrícula para teres acesso aos bilhetes de estudante."
      action={
        badge && (
          <span
            className={`inline-flex shrink-0 items-center gap-1.5 self-start border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${badge.className}`}
          >
            <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
            {badge.label}
          </span>
        )
      }
    >
      {/* `aria-live` e não `role="status"`: esse fica para «A carregar…» (PageStatus). */}
      <p aria-live="polite" aria-atomic="true" className={notice ? "mb-4 mt-0 text-[14px] font-bold text-white" : "sr-only"}>
        {notice}
      </p>

      {current === "verified" && (
        <p className="m-0 text-[14px] text-cinza-texto">
          A tua conta está verificada como estudante. Já podes{" "}
          <Link className="font-bold text-acento-principal underline" to="/bilhetes/checkout">
            comprar um bilhete de estudante
          </Link>
          . Leva o Cartão de Cidadão: à entrada confirmamos que o nome é o do comprovativo.
        </p>
      )}

      {current === "submitted" && (
        <p className="m-0 text-[14px] text-cinza-texto">
          Recebemos o teu comprovativo. Alguém da organização vai revê-lo e o resultado aparece aqui. Até lá, as
          modalidades de estudante ficam fechadas.
        </p>
      )}

      {current === "rejected" && (
        <div className="mb-6 border border-coral-vivo/45 bg-coral-vivo/[0.04] p-5">
          <h3 className="m-0 text-[15px] font-bold text-white">Porque não tens o preço de estudante</h3>
          <p className="mb-0 mt-2 text-[14px] text-nevoa-azul">
            Não conseguimos confirmar o teu comprovativo de matrícula. Para ser aceite, tem de cumprir tudo o que está
            abaixo. Podes enviar outro ou escrever-nos para{" "}
            <a className="font-bold text-acento-principal underline" href={`mailto:${ORGANIZATION_EMAIL}`}>
              {ORGANIZATION_EMAIL}
            </a>
            .
          </p>
        </div>
      )}

      {(current === "none" || current === "rejected") && (
        <ProofForm onStatusChange={onSent} onStale={onStale} />
      )}
    </AccountPanel>
  );
}

function ProofForm({ onStatusChange, onStale }: Omit<StudentProofSectionProps, "status">) {
  const navigate = useNavigate();
  const inputId = useId();
  const helpId = useId();
  const errorId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (sending) return;
    const invalid = studentProofFileError(file);
    if (invalid || !file) {
      setError(invalid);
      return;
    }
    setError(null);
    setSending(true);
    try {
      const { status } = await sendStudentProof(file);
      onStatusChange(status);
    } catch (err) {
      const failure = studentProofError(err);
      if (failure.sessionEnded) {
        navigate("/conta?sessao=terminada", { replace: true });
        return;
      }
      setError(failure.message);
      if (failure.stale) onStale();
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      <div>
        <p className="m-0 text-[13px] font-bold text-white">O comprovativo tem de ter:</p>
        <ul className="mb-0 mt-2 flex list-disc flex-col gap-1 pl-5 text-[13px] text-cinza-texto">
          {STUDENT_PROOF_RULES.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor={inputId} className="text-[13px] font-bold text-white">
          Ficheiro do comprovativo
        </label>
        <input
          id={inputId}
          type="file"
          name="file"
          accept={STUDENT_PROOF_ACCEPT}
          aria-describedby={error ? `${helpId} ${errorId}` : helpId}
          aria-invalid={Boolean(error)}
          disabled={sending}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setError(null);
          }}
          className="w-full min-w-0 max-w-full text-[13px] text-cinza-texto file:mr-3 file:cursor-pointer file:rounded-full file:border-0 file:bg-white/10 file:px-4 file:py-2 file:text-[12px] file:font-bold file:text-white hover:file:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acento-principal"
        />
        <small id={helpId} className="text-[12px] text-cinza-texto">
          PDF, JPG ou PNG, até 1 MB. Só a organização o vê e é apagado depois da decisão.
        </small>
        {error && (
          <p id={errorId} role="alert" className="m-0 text-[13px] text-coral-vivo">
            {error}
          </p>
        )}
      </div>

      <button
        type="submit"
        disabled={sending}
        aria-busy={sending}
        className="self-start rounded-full bg-acento-principal px-5 py-2.5 text-[12px] font-bold uppercase tracking-wide text-texto-de-acao transition-colors hover:bg-acento-principal/90 disabled:cursor-wait disabled:opacity-70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-branco"
      >
        {sending ? "A enviar…" : "Enviar comprovativo"}
      </button>
    </form>
  );
}
