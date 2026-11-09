import type { InputHTMLAttributes } from "react";

type FieldProps = {
  label: string;
  error?: string[];
} & InputHTMLAttributes<HTMLInputElement>;

export default function Field({ label, error, ...props }: FieldProps) {
  const hasError = !!error?.length;
  const errorId = props.name ? `${props.name}-error` : undefined;

  return (
    <div className="grid gap-1.5">
      <label className="grid gap-2">
        <span className="font-montserrat text-xs font-semibold text-gelo">{label}</span>
        <input
          {...props}
          aria-invalid={hasError || undefined}
          aria-describedby={hasError ? errorId : undefined}
          className="h-[52px] w-full rounded-[2px] border border-[rgba(215,227,244,0.1)] bg-azul-base px-4 text-white outline-none placeholder:text-cinza-subtil focus:border-acento-principal focus:shadow-[0_0_0_3px_rgba(26,178,255,0.13)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acento-principal aria-[invalid=true]:border-red-400"
        />
      </label>
      {hasError && (
        <div id={errorId} className="grid gap-0.5">
          {error!.map((m) => (
            <p key={m} role="alert" className="m-0 text-[12px] text-red-400">
              {m}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}