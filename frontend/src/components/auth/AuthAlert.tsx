import type { Ref } from "react";

/** Aviso de erro do formulário. Recebe o foco depois de um erro sem campo (ver `useAuthForm`). */
export default function AuthAlert({ message, alertRef }: { message: string | null; alertRef: Ref<HTMLParagraphElement> }) {
  if (!message) return null;
  return (
    <p ref={alertRef} role="alert" tabIndex={-1} className="auth-alert">
      {message}
    </p>
  );
}
