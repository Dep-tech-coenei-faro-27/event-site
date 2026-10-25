import { useState, type SyntheticEvent } from "react";
import AccountLayout from "../components/dashboard/AccountLayout";
import AccountPanel from "../components/dashboard/AccountPanel";
import { panelClass, panelTitleClass } from "../components/dashboard/AccountStyles";
import Eyebrow from "../components/EyeBrow";
import Field from "../components/Field";
import PrimaryButton from "../components/PrimaryButton";
import SecondaryButton from "../components/SecundaryButton";
import { ApiError, http } from "../utils/http";
import { useAuth } from "../utils/useAuth";
import { validationMessages } from "../utils/ValidationErrors";
import { CONTACT_PHONE_MESSAGE, isContactPhone, normalizeContactPhone } from "../utils/contactPhone";

/**
 * Dados pessoais: usa o mesmo layout (hero + barra lateral) da visão geral.
 * O backend só deixa mudar o nome (`PUT /api/users/me`; o email não se altera), por isso só o nome é editável:
 * o email mostra-se, não se finge guardar. A instituição e o curso deixaram de se mostrar.
 */
export default function DadosPessoais() {
  const { user: me, refresh } = useAuth();

  const [name, setName] = useState(me?.name ?? "");
  const [phone, setPhone] = useState(me?.phone ?? "");
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (saving) return;
    setSaveStatus(null);
    setSaveError(null);
    setPhoneError(null);

    const trimmed = name.trim();
    if (!trimmed) {
      setSaveError("Indica o teu nome.");
      return;
    }

    const phoneText = phone.trim();
    if (phoneText && !isContactPhone(phoneText)) {
      setPhoneError(CONTACT_PHONE_MESSAGE);
      return;
    }
    const contact = phoneText ? normalizeContactPhone(phoneText) : null;

    setSaving(true);
    try {
      await http("/users/me", { method: "PUT", body: { name: trimmed, phone: contact } });
      setPhone(contact ?? "");
      await refresh();
      setSaveStatus("Dados atualizados.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        const messages = validationMessages(err.detail);
        setSaveError(messages.length ? messages.join(" ") : "O nome não é válido.");
      } else if (err instanceof ApiError && err.status === 403) {
        setSaveError("Confirma o teu email antes de alterares os dados.");
      } else if (err instanceof ApiError) {
        setSaveError("Não foi possível guardar. Tenta novamente.");
      } else {
        setSaveError("Não foi possível contactar o servidor.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleExportData = () => {
    if (!me) return;

    // Só o que a conta tem hoje no navegador; a exportação completa (pagamentos, NIF...) vem do servidor (#123).
    const payload = {
      exported_at: new Date().toISOString(),
      profile: {
        id: me.id,
        name: me.name,
        email: me.email,
        is_verified: me.is_verified,
      },
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "enei-2027-dados-pessoais.json";
    a.click();
    URL.revokeObjectURL(url);

    setExportStatus("Ficheiro de dados exportado.");
  };

  return (
    <AccountLayout
      metaTitle="Dados pessoais · ENEI 2027"
      metaDescription="Definições de dados pessoais da conta ENEI 2027."
      eyebrow="ÁREA PESSOAL"
      title="Dados pessoais."
      lead="Mantém atualizada a informação utilizada na inscrição e no bilhete."
    >
      {/* Cabeçalho da vista (.account-view-heading) */}
      <div className="mb-1">
        <Eyebrow text="DEFINIÇÕES" />
        <h2 className={panelTitleClass}>Dados pessoais</h2>
        <p className="mb-0 mt-1.5 text-[14px] text-cinza-texto">
          Informação utilizada na inscrição e no bilhete.
        </p>
      </div>

      {/* Painel Principal: Formulário de Dados Pessoais (#dados) */}
      <AccountPanel
        id="dados"
        eyebrow="PERFIL"
        title="Dados pessoais"
        description="Mantém a informação da tua conta atualizada."
      >
        <form className="grid gap-[18px]" onSubmit={handleSubmit}>
          <Field
            label="Nome completo"
            name="name"
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setSaveStatus(null);
              setSaveError(null);
            }}
            autoComplete="name"
            required
          />

          <Field
            label="Contacto"
            name="phone"
            type="tel"
            inputMode="tel"
            value={phone}
            onChange={(e) => {
              setPhone(e.target.value);
              setPhoneError(null);
              setSaveStatus(null);
              setSaveError(null);
            }}
            autoComplete="tel"
            placeholder="912 345 678"
            error={phoneError ? [phoneError] : undefined}
          />
          <p className="-mt-2 m-0 text-[12px] text-cinza-texto">
            Opcional. Para a organização falar contigo sobre a tua participação.
          </p>

          <Field label="Email" name="email" type="email" value={me?.email ?? ""} readOnly />
          <p className="-mt-2 m-0 text-[12px] text-cinza-texto">
            {me?.is_verified === false
              ? "O endereço de email aguarda verificação. Não se pode alterar."
              : "O endereço de email está verificado. Não se pode alterar."}
          </p>

          {saveError && (
            <p role="alert" className="m-0 text-[13px] text-coral-vivo">
              {saveError}
            </p>
          )}

          {saveStatus && (
            <p
              role="status"
              className="m-0 border-l-[3px] border-acento-principal bg-[rgba(26,178,255,0.07)] px-3.5 py-2.5 text-xs text-cinza-texto"
            >
              {saveStatus}
            </p>
          )}

          <div className="pt-1">
            <PrimaryButton
              type="submit"
              text={saving ? "A guardar…" : "Guardar alterações"}
              disabled={saving}
              className="w-full !h-[52px] !rounded-[2px] !text-[12px] uppercase tracking-[0.06em]"
            />
          </div>
        </form>
      </AccountPanel>

      {/* Painel de Privacidade e Exportação (.account-privacy-panel) */}
      <section
        aria-labelledby="export-data-title"
        className={`${panelClass} flex flex-col justify-between gap-5 border-acento-principal/30 bg-[linear-gradient(145deg,rgba(26,178,255,0.06),transparent_60%)] min-[768px]:flex-row min-[768px]:items-center`}
      >
        <div className="max-w-[540px]">
          <Eyebrow text="PRIVACIDADE E DADOS" />
          <h2 id="export-data-title" className={panelTitleClass}>
            Leva contigo uma cópia dos teus dados.
          </h2>
          <p className="mb-0 mt-2 text-[13px] leading-relaxed text-cinza-texto">
            Exporta num ficheiro legível os dados do perfil e o estado da verificação.
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-start gap-2.5 min-[768px]:items-end">
          <SecondaryButton
            type="button"
            text="Exportar os meus dados"
            onClick={handleExportData}
            className={`max-[620px]:w-full !h-[48px] !rounded-[2px] !border-[rgba(215,227,244,0.16)] !bg-white/[0.03] !text-[12px] uppercase tracking-[0.06em] hover:!border-white/35 hover:!bg-white/[0.07]`}
          />
          {exportStatus && (
            <p role="status" className="m-0 text-[12px] text-cinza-texto">
              {exportStatus}
            </p>
          )}
        </div>
      </section>
    </AccountLayout>
  );
}
