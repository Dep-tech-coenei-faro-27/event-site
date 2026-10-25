import { passwordRules } from "../utils/passwordChange";

/**
 * As regras da palavra-passe (as mesmas do backend), a verificar-se ao vivo enquanto se escreve.
 * `conta` usa o desenho das páginas de autenticação (`.password-rules` de `conta.css`);
 * `painel` o da área pessoal.
 */
export default function PasswordRules({ password, variant }: { password: string; variant: "conta" | "painel" }) {
  return (
    <ul
      aria-label="Requisitos da palavra-passe"
      className={variant === "conta" ? "password-rules" : "m-0 grid list-none gap-1.5 p-0"}
    >
      {passwordRules.map((rule) => {
        const ok = rule.test(password);
        return (
          <li
            key={rule.code}
            data-ok={ok}
            className={
              variant === "painel"
                ? `flex items-center gap-2 text-[11px] transition-colors ${ok ? "text-acento-forte" : "text-cinza-subtil"}`
                : undefined
            }
          >
            {variant === "painel" && (
              <span aria-hidden="true" className="text-acento-principal">
                {ok ? "✓" : "—"}
              </span>
            )}
            {rule.label}
            <span className="sr-only">{ok ? " (cumprido)" : " (por cumprir)"}</span>
          </li>
        );
      })}
    </ul>
  );
}
