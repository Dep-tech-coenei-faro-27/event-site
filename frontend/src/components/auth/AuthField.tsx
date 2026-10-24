import type { InputHTMLAttributes } from "react";

type Props = {
  label: string;
  name: string;
  /** Mensagens do servidor (ou da validação) para este campo. */
  error?: string[];
} & InputHTMLAttributes<HTMLInputElement>;

/** Campo do desenho novo (`.auth-field`), com o erro ligado por `aria-describedby`. */
export default function AuthField({ label, name, error, ...props }: Props) {
  const hasError = !!error?.length;
  const errorId = `${name}-error`;
  return (
    <div className="grid gap-1.5">
      <label className="auth-field">
        <span>{label}</span>
        <input
          {...props}
          name={name}
          aria-invalid={hasError || undefined}
          aria-describedby={hasError ? errorId : undefined}
        />
      </label>
      {hasError && (
        <div id={errorId}>
          {error!.map((message) => (
            <p key={message} className="auth-field-error">
              {message}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
