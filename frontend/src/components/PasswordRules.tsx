import { passwordRules } from "../utils/passwordChange";

/** As regras da nova palavra-passe, a verificar-se ao vivo enquanto se escreve (as mesmas do backend). */
export default function PasswordRules({ password }: { password: string }) {
  return (
    <ul aria-label="Requisitos da nova palavra-passe" className="m-0 grid list-none gap-1.5 p-0">
      {passwordRules.map((rule) => {
        const ok = rule.test(password);
        return (
          <li
            key={rule.label}
            data-ok={ok}
            className={`flex items-center gap-2 text-[11px] transition-colors ${
              ok ? "text-acento-forte" : "text-cinza-subtil"
            }`}
          >
            <span aria-hidden="true" className="text-acento-principal">
              {ok ? "✓" : "—"}
            </span>
            {rule.label}
            <span className="sr-only">{ok ? " (cumprido)" : " (por cumprir)"}</span>
          </li>
        );
      })}
    </ul>
  );
}
