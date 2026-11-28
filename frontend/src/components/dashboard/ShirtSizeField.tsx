import { useState } from "react";
import { setShirtSize } from "../../payments/api";
import { SHIRT_SIZES, type AccountTicket, type ShirtSize } from "../../payments/types";
import { ApiError, NetworkError } from "../../utils/http";
import { BORDER } from "./AccountStyles";

/** Texto para quem não conseguiu guardar o tamanho. */
function shirtError(error: unknown): string {
  if (error instanceof NetworkError) return "Sem ligação. Verifica a rede e tenta outra vez.";
  if (error instanceof ApiError) {
    if (error.status === 409) return "Já não é possível mudar o tamanho: a lista da camisola fechou.";
    if (error.status === 401) return "A tua sessão terminou. Entra outra vez para continuar.";
  }
  return "Não foi possível guardar o tamanho. Tenta outra vez.";
}

/** O tamanho da camisola do bilhete de estudante: mostra-se e muda-se até à data limite. */
export default function ShirtSizeField({ ticket, onSaved }: { ticket: AccountTicket; onSaved: () => void }) {
  const saved = ticket.shirt_size ?? "";
  const [choice, setChoice] = useState<ShirtSize | "">(saved);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const canChange = ticket.shirt_can_change === true;

  async function save() {
    if (choice === "" || saving) return;
    setSaving(true);
    setMessage(null);
    try {
      await setShirtSize(choice);
      setMessage({ ok: true, text: "Tamanho guardado." });
      onSaved();
    } catch (error) {
      setMessage({ ok: false, text: shirtError(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section id="camisola" aria-labelledby="shirt-heading" className={`border-t ${BORDER} px-5 py-4 min-[621px]:px-6`}>
      <h3 id="shirt-heading" className="m-0 text-[13px] font-bold text-white">
        Camisola do ENEI
      </h3>
      {saved === "" && canChange && (
        <p role="status" className="mb-0 mt-1.5 text-[12px] text-acento-principal">
          Ainda não escolheste o tamanho. Escolhe-o abaixo: a lista fecha quando as camisolas forem encomendadas.
        </p>
      )}
      {canChange ? (
        <div className="mt-3 flex flex-wrap items-center gap-2.5">
          <label htmlFor="shirt-size" className="text-[12px] text-cinza-texto">
            Tamanho (unissexo)
          </label>
          <select
            id="shirt-size"
            value={choice}
            onChange={(event) => {
              setChoice(event.target.value as ShirtSize | "");
              setMessage(null);
            }}
            className={`h-11 min-w-[120px] rounded-[2px] border ${BORDER} bg-transparent px-3 text-[13px] font-bold text-white`}
          >
            <option value="" disabled>
              Escolhe
            </option>
            {SHIRT_SIZES.map((size) => (
              <option key={size} value={size} className="text-black">
                {size}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving || choice === "" || choice === saved}
            className={`h-11 rounded-[2px] border ${BORDER} bg-transparent px-4 text-[12px] font-semibold text-[#d7e3f4] transition-colors hover:bg-white/5 disabled:cursor-default disabled:opacity-60 disabled:hover:bg-transparent`}
          >
            {saving ? "A guardar…" : "Guardar"}
          </button>
        </div>
      ) : (
        <p className="mb-0 mt-1.5 text-[13px] text-white">
          {saved === "" ? "Sem tamanho escolhido." : `Tamanho ${saved} (unissexo).`}{" "}
          <span className="text-cinza-texto">A lista da camisola já fechou.</span>
        </p>
      )}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={`mb-0 mt-2 text-[12px] ${message.ok ? "text-[#10b981]" : "text-[#f6d2cd]"}`}>
          {message.text}
        </p>
      )}
    </section>
  );
}
