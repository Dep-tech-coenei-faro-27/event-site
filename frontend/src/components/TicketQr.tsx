import { QRCodeSVG } from "qrcode.react";

interface TicketQrProps {
  /** A String vinda do backend */
  code: string;
  size?: number;
  className?: string;
}

const MIN_SIZE = 132;

export default function TicketQr({
  code,
  size = 136,
  className = "",
}: TicketQrProps) {
  return (
    <figure className={`m-0 flex flex-col items-center ${className}`}>
      {/* .account-pass__qr-frame */}
      <div className="border border-[rgba(215,227,244,0.12)] bg-white/[0.03] p-2">
        <div className="bg-white p-2.5">
          <QRCodeSVG
            value={code}
            size={size}
            level="M"
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
        </div>
      </div>

      {/* .account-pass__code-ref */}
      <figcaption className="mt-3.5 flex w-full justify-center">
        <strong className="max-w-[210px] select-all break-all border border-[rgba(215,227,244,0.12)] bg-white/[0.02] px-3.5 py-1.5 text-center font-mono text-[11px] font-bold tracking-wide text-white">
          Código · {code}
        </strong>
      </figcaption>
    </figure>
  );
}