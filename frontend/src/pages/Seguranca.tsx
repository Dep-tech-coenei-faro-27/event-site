import { useState, type SyntheticEvent } from "react";
import AccountLayout from "../components/dashboard/AccountLayout";
import AccountPanel from "../components/dashboard/AccountPanel";
import { BORDER, panelTitleClass } from "../components/dashboard/AccountStyles";
import Eyebrow from "../components/EyeBrow";
import Field from "../components/Field";
import SecondaryButton from "../components/SecundaryButton";
import { http } from "../utils/http";
import { passwordChangeMessage, passwordFormError } from "../utils/passwordChange";
import { useAuth } from "../utils/useAuth";

/** Segurança: usa o mesmo layout (hero + barra lateral) da visão geral. */
export default function Seguranca() {
  const { user: me } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordStatus, setPasswordStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // PUT /api/auth/password: a API devolve uma sessão nova e termina as sessões noutros dispositivos.
  const handlePasswordSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (saving) return;
    setPasswordError(null);
    setPasswordStatus(null);

    const problem = passwordFormError(currentPassword, newPassword, confirmPassword);
    if (problem) {
      setPasswordError(problem);
      return;
    }

    setSaving(true);
    try {
      await http("/auth/password", {
        method: "PUT",
        body: { current_password: currentPassword, new_password: newPassword },
      });
      setPasswordStatus("Palavra-passe atualizada. As sessões noutros dispositivos foram terminadas.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(passwordChangeMessage(err));
    } finally {
      setSaving(false);
    }
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
              text={saving ? "A guardar…" : "Alterar palavra-passe"}
              disabled={saving}
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
              {me ? (me.is_verified ? "Verificado" : "Pendente") : "—"}
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
    </AccountLayout>
  );
}