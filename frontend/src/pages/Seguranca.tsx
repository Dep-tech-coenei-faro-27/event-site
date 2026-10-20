import { useRef, useState, type SyntheticEvent } from "react";
import AccountLayout from "../components/dashboard/AccountLayout";
import AccountPanel from "../components/dashboard/AccountPanel";
import { BORDER, panelTitleClass } from "../components/dashboard/AccountStyles";
import Eyebrow from "../components/EyeBrow";
import Field from "../components/Field";
import SecondaryButton from "../components/SecundaryButton";
import { useAuth } from "../utils/useAuth";

/** Segurança: usa o mesmo layout (hero + barra lateral) da visão geral. */
export default function Seguranca() {
  const { user: me } = useAuth();

  // Estado do formulário de alteração de palavra-passe
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordStatus, setPasswordStatus] = useState<string | null>(null);

  // Estado da Zona Crítica / Modal de eliminação de conta
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteStatus, setDeleteStatus] = useState<string | null>(null);

  const canDelete = deleteConfirmText.trim() === "ELIMINAR";

  const handlePasswordSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordStatus(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("As palavras-passe não coincidem.");
      return;
    }

    setPasswordStatus("Palavra-passe atualizada.");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  const openDeleteDialog = () => {
    setDeleteConfirmText("");
    dialogRef.current?.showModal();
  };

  const closeDeleteDialog = () => {
    setDeleteConfirmText("");
    dialogRef.current?.close();
  };

  const handleConfirmDelete = () => {
    if (!canDelete) return;
    closeDeleteDialog();
    setDeleteStatus("Pedido de eliminação registado.");
  };

  return (
    <AccountLayout
      metaTitle="Segurança · ENEI 2027"
      metaDescription="Definições de segurança da conta ENEI 2027."
      eyebrow="ÁREA PESSOAL"
      title="Segurança da conta."
      lead="Atualiza a palavra-passe e consulta o estado de proteção do perfil."
    >
      {/* Cabeçalho da vista (.account-view-heading) */}
      <div className="mb-1">
        <Eyebrow text="DEFINIÇÕES" />
        <h2 className={panelTitleClass}>Segurança</h2>
        <p className="mb-0 mt-1.5 text-[14px] text-cinza-texto">
          Protege o acesso à tua conta ENEI.
        </p>
      </div>

      {/* Painel Principal: Acesso à conta (#seguranca) */}
      <AccountPanel
        id="seguranca"
        eyebrow="SEGURANÇA"
        title="Acesso à conta"
        description="Atualiza a palavra-passe e revê a segurança do perfil."
      >
        <form className="grid gap-[18px]" onSubmit={handlePasswordSubmit}>
          <Field
            label="Palavra-passe atual"
            name="current_password"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
            placeholder="A tua palavra-passe atual"
            required
          />

          <div className="grid gap-[18px] min-[621px]:grid-cols-2">
            <Field
              label="Nova palavra-passe"
              name="new_password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              placeholder="Nova palavra-passe"
              required
            />
            <Field
              label="Confirmar palavra-passe"
              name="confirm_password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              placeholder="Repete a palavra-passe"
              required
            />
          </div>

          {passwordError && (
            <p role="alert" className="m-0 text-[13px] text-coral-vivo">
              {passwordError}
            </p>
          )}

          {passwordStatus && (
            <p
              role="status"
              className="m-0 border-l-[3px] border-acento-principal bg-[rgba(26,178,255,0.07)] px-3.5 py-2.5 text-xs text-cinza-texto"
            >
              {passwordStatus}
            </p>
          )}

          <div className="pt-1">
            <SecondaryButton
              type="submit"
              text="Alterar palavra-passe"
              className="w-full !h-[52px] !rounded-[2px] !border-[rgba(215,227,244,0.16)] !bg-white/[0.03] !text-[12px] uppercase tracking-[0.06em] hover:!border-white/35 hover:!bg-white/[0.07]"
            />
          </div>
        </form>

        {/* Resumo de segurança (.account-security-summary) */}
        <div
          className={`mt-7 grid grid-cols-1 gap-4 border-t ${BORDER} pt-7 min-[621px]:grid-cols-2`}
        >
          <div className={`border ${BORDER} bg-azul-base/60 px-5 py-4`}>
            <span className="block font-montserrat text-[10px] font-semibold uppercase tracking-[0.14em] text-cinza-subtil">
              Email
            </span>
            <strong className="mt-1.5 block text-[15px] font-bold text-white">
              {me?.is_verified === false ? "Pendente" : "Verificado"}
            </strong>
          </div>
          <div className={`border ${BORDER} bg-azul-base/60 px-5 py-4`}>
            <span className="block font-montserrat text-[10px] font-semibold uppercase tracking-[0.14em] text-cinza-subtil">
              Sessão atual
            </span>
            <strong className="mt-1.5 block text-[15px] font-bold text-white">
              Este dispositivo
            </strong>
          </div>
        </div>
      </AccountPanel>

      {/* Zona Crítica (.account-danger-zone) */}
      <section
        aria-labelledby="delete-account-title"
        className="flex flex-col justify-between gap-5 border border-coral-suave/35 bg-[linear-gradient(145deg,rgba(238,145,133,0.07),transparent_60%)] bg-azul-painel px-5 py-6 min-[621px]:p-7 min-[768px]:flex-row min-[768px]:items-center"
      >
        <div className="max-w-[540px]">
          <p className="m-0 mb-3.5 font-montserrat text-[11px] font-bold uppercase leading-[1.4] tracking-[0.16em] text-coral-suave">
            &lt;ZONA CRÍTICA /&gt;
          </p>
          <h2 id="delete-account-title" className={panelTitleClass}>
            Apagar a conta
          </h2>
          <p className="mb-0 mt-2 text-[13px] leading-relaxed text-cinza-texto">
            Esta ação é permanente. Antes de continuares, exporta os teus dados e
            confirma que já não precisas de aceder ao bilhete.
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-start gap-2.5 min-[768px]:items-end">
          <SecondaryButton
            type="button"
            text="Apagar a minha conta"
            onClick={openDeleteDialog}
            className="max-[620px]:w-full !border-coral-suave/45 !text-coral-suave hover:!border-coral-vivo hover:!bg-coral-suave/10 hover:!text-white"
          />
          {deleteStatus && (
            <p role="status" className="m-0 text-[12px] text-cinza-texto">
              {deleteStatus}
            </p>
          )}
        </div>
      </section>

      {/* Modal de confirmação (.account-confirm-dialog) */}
      <dialog
        ref={dialogRef}
        aria-labelledby="delete-dialog-title"
        onClick={(e) => {
          if (e.target === dialogRef.current) closeDeleteDialog();
        }}
        className={`m-auto w-[min(calc(100%-28px),460px)] border ${BORDER} bg-azul-painel p-0 text-white shadow-2xl backdrop:bg-black/75 backdrop:backdrop-blur-sm`}
      >
        <div className="p-6 min-[621px]:p-7">
          <div
            aria-hidden="true"
            className="mb-4 grid size-11 place-items-center rounded-full border border-coral-suave/45 bg-coral-suave/10 font-montserrat text-base font-extrabold text-coral-suave"
          >
            !
          </div>

          <h2
            id="delete-dialog-title"
            className="text-[clamp(22px,2.6vw,28px)] font-bold leading-tight tracking-[-0.03em] text-white"
          >
            Tens a certeza?
          </h2>

          <p className="mb-5 mt-2.5 text-[13px] leading-relaxed text-cinza-texto">
            A conta, o perfil e o acesso ao bilhete deixam de estar disponíveis.
            Para confirmar, escreve <strong className="text-white">ELIMINAR</strong>.
          </p>

          <Field
            label="Confirmação"
            type="text"
            autoComplete="off"
            placeholder="Escreve ELIMINAR"
            value={deleteConfirmText}
            onChange={(e) => setDeleteConfirmText(e.target.value)}
          />

          <div className="mt-6 flex flex-col-reverse gap-3 min-[520px]:flex-row min-[520px]:justify-end">
            <SecondaryButton
              type="button"
              text="Cancelar"
              onClick={closeDeleteDialog}
            />
            <button
              type="button"
              disabled={!canDelete}
              onClick={handleConfirmDelete}
              className="inline-flex min-h-[46px] cursor-pointer items-center justify-center rounded-full border border-coral-suave/50 bg-coral-suave px-6 font-montserrat text-[14px] font-bold text-[#02101c] transition hover:bg-coral-vivo disabled:cursor-not-allowed disabled:opacity-40"
            >
              Apagar definitivamente
            </button>
          </div>
        </div>
      </dialog>
    </AccountLayout>
  );
}