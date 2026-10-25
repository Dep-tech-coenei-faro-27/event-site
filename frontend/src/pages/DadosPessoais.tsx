import { useState, type SyntheticEvent } from "react";
import AccountLayout from "../components/dashboard/AccountLayout";
import AccountPanel from "../components/dashboard/AccountPanel";
import { panelClass, panelTitleClass } from "../components/dashboard/AccountStyles";
import Eyebrow from "../components/EyeBrow";
import Field from "../components/Field";
import PrimaryButton from "../components/PrimaryButton";
import SecondaryButton from "../components/SecundaryButton";
import { http } from "../utils/http";
import { nameErrors, profileSaveError } from "../utils/profileName";
import { useAuth } from "../utils/useAuth";

/**
 * Dados pessoais: usa o mesmo layout (hero + barra lateral) da visão geral.
 * O backend só deixa mudar o nome (`PUT /api/users/me`; a instituição e o curso são listas fechadas e o
 * email não se altera), por isso só o nome é editável: o resto mostra-se, não se finge guardar.
 */
export default function DadosPessoais() {
  const { user: me, refresh } = useAuth();

  const [name, setName] = useState(me?.name ?? "");
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string[]>([]);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (saving) return;
    setSaveStatus(null);
    setSaveError(null);

    // As mesmas regras do servidor: um nome inválido nem chega a ser enviado.
    const errors = nameErrors(name);
    setNameError(errors);
    if (errors.length) {
      document.getElementById("name")?.focus();
      return;
    }
    const trimmed = name.trim();

    setSaving(true);
    try {
      await http("/users/me", { method: "PUT", body: { name: trimmed } });
      await refresh();
      setSaveStatus("Dados atualizados.");
    } catch (err) {
      // Um 422 do nome aparece no próprio campo; o resto, no fim do formulário.
      const failure = profileSaveError(err);
      if (failure.name) {
        setNameError(failure.name);
        document.getElementById("name")?.focus();
      }
      if (failure.form) setSaveError(failure.form);
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
        institution: me.institution ?? null,
        course: me.course ?? null,
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
            id="name"
            name="name"
            type="text"
            value={name}
            error={nameError}
            onChange={(e) => {
              setName(e.target.value);
              setSaveStatus(null);
              setSaveError(null);
              setNameError([]);
            }}
            autoComplete="name"
            required
          />

          <Field label="Email" name="email" type="email" value={me?.email ?? ""} readOnly />
          <p className="-mt-2 m-0 text-[12px] text-cinza-texto">
            {me?.is_verified === false
              ? "O endereço de email aguarda verificação. Não se pode alterar."
              : "O endereço de email está verificado. Não se pode alterar."}
          </p>

          <div className="grid gap-[18px] min-[621px]:grid-cols-2">
            <Field label="Instituição" name="institution" type="text" value={me?.institution ?? "—"} readOnly />
            <Field label="Curso" name="course" type="text" value={me?.course ?? "—"} readOnly />
          </div>

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
