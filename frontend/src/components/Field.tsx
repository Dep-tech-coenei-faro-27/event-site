import type { InputHTMLAttributes } from "react";

type FieldProps = { label: string } & InputHTMLAttributes<HTMLInputElement>;

export default function Field({ label, ...props }: FieldProps) {
  return (
    <label className="grid gap-2">
      <span className="font-montserrat text-xs font-semibold text-gelo">{label}</span>
      <input
        {...props}
        className="h-[52px] w-full rounded-[2px] border border-[rgba(215,227,244,0.1)] bg-azul-base px-4 text-white outline-none placeholder:text-cinza-subtil focus:border-acento-principal focus:shadow-[0_0_0_3px_rgba(26,178,255,0.13)]"
      />
    </label>
  );
}