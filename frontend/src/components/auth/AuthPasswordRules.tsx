import { passwordRules } from "../../utils/passwordChange";

/** As regras da palavra-passe no desenho de `ui-ux/conta` (`.password-rules`), a verificar-se ao vivo. */
export default function AuthPasswordRules({ password }: { password: string }) {
  return (
    <ul className="password-rules" aria-label="Requisitos da palavra-passe">
      {passwordRules.map((rule) => {
        const ok = rule.test(password);
        return (
          <li key={rule.label} data-ok={ok}>
            {rule.label}
            <span className="sr-only">{ok ? " (cumprido)" : " (por cumprir)"}</span>
          </li>
        );
      })}
    </ul>
  );
}
