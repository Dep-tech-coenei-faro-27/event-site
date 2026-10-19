import { useCallback, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { QRCodeSVG } from "qrcode.react";

interface TicketQrProps {
  /** A String vinda do backend */
  code: string;
  size?: number;
  className?: string;
}

const MIN_SIZE = 168;
const FRAME = "border border-[rgba(215,227,244,0.12)]";

/**
 * QR ampliado por cima da página, para a leitura à porta. Fecha com o X, com um clique fora
 * do QR ou com Esc, e deixa a página exatamente onde estava: não mexe no scroll nem no layout.
 */
function QrPreview({ code, onClose }: { code: string; onClose: () => void }) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // Bloqueia o scroll por baixo sem deslocar o layout (a barra de scroll desaparece, por
    // isso o espaço dela fica reservado) e repõe tudo ao fechar.
    const { body, documentElement: html } = document;
    const previous = { overflow: body.style.overflow, paddingRight: body.style.paddingRight };
    const scrollbar = window.innerWidth - html.clientWidth;
    if (scrollbar > 0) {
      const current = parseFloat(getComputedStyle(body).paddingRight) || 0;
      body.style.paddingRight = `${current + scrollbar}px`;
    }
    body.style.overflow = "hidden";

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    closeRef.current?.focus({ preventScroll: true });

    return () => {
      document.removeEventListener("keydown", onKey);
      body.style.overflow = previous.overflow;
      body.style.paddingRight = previous.paddingRight;
    };
  }, [onClose]);

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      data-testid="qr-preview"
      onClick={onClose}
      className="fixed inset-0 z-[300] flex items-center justify-center bg-black/55 p-4"
    >
      <h2 id={titleId} className="sr-only">
        Código QR do teu bilhete, ampliado
      </h2>

      <button
        ref={closeRef}
        type="button"
        aria-label="Fechar o QR ampliado"
        onClick={onClose}
        className="fixed right-4 top-4 grid size-11 place-items-center border border-white/30 bg-black/60 text-2xl leading-none text-white transition-colors hover:bg-black/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
      >
        <span aria-hidden="true">×</span>
      </button>

      {/* Clicar no próprio QR (ou na moldura) não fecha: só o que está fora dele.
          A moldura é a mesma do QR pequeno da página da conta. */}
      <div
        onClick={(e) => e.stopPropagation()}
        className={`${FRAME} bg-white/[0.03] p-3 shadow-[0_20px_60px_rgba(0,0,0,0.5)] sm:p-4`}
      >
        <div className="bg-white p-5 sm:p-7">
          <QRCodeSVG
            value={code}
            level="Q"
            marginSize={0}
            bgColor="#ffffff"
            fgColor="#000000"
            role="img"
            aria-label="Código QR do teu bilhete, ampliado."
            style={{
              display: "block",
              width: "min(84vw, 80vh, 560px)",
              height: "auto",
              aspectRatio: "1 / 1",
            }}
          />
        </div>
      </div>
    </div>,
    document.body,
  );
}

export default function TicketQr({
  code,
  size = 200,
  className = "",
}: TicketQrProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  // Estável: o efeito do QR ampliado repõe o scroll no fecho e não pode correr a cada render.
  const close = useCallback(() => {
    setOpen(false);
    // Devolve o foco ao QR pequeno sem deslocar a página.
    triggerRef.current?.focus({ preventScroll: true });
  }, []);

  return (
    <figure className={`m-0 flex flex-col items-center ${className}`}>
      {/* .account-pass__qr-frame */}
      <div className={`${FRAME} bg-white/[0.03] p-2`}>
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setOpen(true)}
          aria-haspopup="dialog"
          aria-label="Ampliar o código QR do bilhete"
          title="Clica para ampliar"
          className="block cursor-zoom-in bg-white p-2.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acento-principal"
        >
          <QRCodeSVG
            value={code}
            size={size}
            level="Q"
            marginSize={0}
            bgColor="#ffffff"
            fgColor="#03101d"
            role="img"
            aria-label="Código QR do teu bilhete. O mesmo código está escrito por baixo."
            style={{
              width: size,
              minWidth: MIN_SIZE,
              maxWidth: "100%",
              height: "auto",
              display: "block",
            }}
          />
        </button>
      </div>

      {/* .account-pass__code-ref */}
      <figcaption className="mt-3.5 flex w-full justify-center">
        <strong
          className={`max-w-[210px] select-all break-all ${FRAME} bg-white/[0.02] px-3.5 py-1.5 text-center font-mono text-[11px] font-bold tracking-wide text-white`}
        >
          Código · {code}
        </strong>
      </figcaption>

      {open && <QrPreview code={code} onClose={close} />}
    </figure>
  );
}
