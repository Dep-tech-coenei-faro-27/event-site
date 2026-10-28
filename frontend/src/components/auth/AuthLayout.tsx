import type { ReactNode } from "react";
import "../../conta.css";
import "../../conta.overrides.css";
import { useBodyPage } from "../../utils/useBodyPage";

type Props = {
  /** Texto da etiqueta da coluna da esquerda, sem os `< />` (por exemplo `CONTA_ENEI`). */
  eyebrow: string;
  title: string;
  lead: string;
  points: string[];
  /** Cartão alinhado ao topo, para formulários compridos (Criar conta). */
  wide?: boolean;
  children: ReactNode;
};

/**
 * Moldura das páginas de entrada do desenho novo (`ui-ux/conta/*`): a apresentação à esquerda e o
 * cartão com o formulário à direita. O CSS (`conta.css`) só se aplica com `body[data-page="conta"]`.
 */
export default function AuthLayout({ eyebrow, title, lead, points, wide = false, children }: Props) {
  useBodyPage("conta");
  return (
    <div className="auth-page">
      <section className="auth-section">
        <div className="container auth-shell">
          <div className="auth-aside">
            <div>
              <p className="eyebrow">&lt;{eyebrow} /&gt;</p>
              <h1>{title}</h1>
              <p className="lead">{lead}</p>
            </div>
            <div className="auth-points">
              {points.map((text, i) => (
                <div className="auth-point" key={text}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  <p>{text}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`auth-card${wide ? " auth-card--wide" : ""}`}>{children}</div>
        </div>
      </section>
    </div>
  );
}

/** Ícone quadrado por cima do título do cartão (só o interior do SVG, em 24×24). */
export function AuthStateIcon({ children }: { children: ReactNode }) {
  return (
    <div className="auth-state-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24">{children}</svg>
    </div>
  );
}

export function AuthEyebrow({ text }: { text: string }) {
  return <p className="eyebrow">&lt;{text} /&gt;</p>;
}
