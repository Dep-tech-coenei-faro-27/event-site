import type { ReactNode } from "react";

type Fact = { label: string; value: string };

type Props = {
  /** Ícone SVG (só o interior, caminhos em 24×24). */
  icon: ReactNode;
  kicker: string;
  title: string;
  lead: ReactNode;
  actions: ReactNode;
  note: string;
  /** Nome da coluna do detalhe para leitores de ecrã (as páginas de erro usam «Detalhes do erro»). */
  detailLabel?: string;
  detail: {
    /** O código grande (401, 422, 429...) ou uma etiqueta (`label`), como no desenho. */
    code: string;
    codeIsLabel?: boolean;
    heading: string;
    text: string;
    /** Algo mais por baixo do texto (por exemplo, o contador). */
    extra?: ReactNode;
    facts: Fact[];
  };
};

/**
 * Estado de sistema do desenho novo (`ui-ux/conta/*`): ecrã com o que aconteceu à esquerda e, à
 * direita, o detalhe. A cor do estado (aviso, perigo) vem da classe no `<body>` (`useBodyPage`).
 */
export default function SystemState({ icon, kicker, title, lead, actions, note, detailLabel = "Detalhes", detail }: Props) {
  return (
    <div className="system-state-main">
      <div className="container">
        <article className="system-state-shell" aria-labelledby="state-title">
          <div className="system-state-content">
            <div className="system-state-heading">
              <div className="system-state-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">{icon}</svg>
              </div>
              <p className="system-state-kicker">{kicker}</p>
            </div>
            <h1 id="state-title">{title}</h1>
            <p className="system-state-lead">{lead}</p>
            <div className="system-state-actions">{actions}</div>
            <p className="system-state-note">{note}</p>
          </div>
          <aside className="system-state-detail" aria-label={detailLabel}>
            <div>
              <div className={`system-state-code${detail.codeIsLabel ? " system-state-code--label" : ""}`} aria-hidden="true">
                {detail.code}
              </div>
              <h2>{detail.heading}</h2>
              <p>{detail.text}</p>
              {detail.extra}
            </div>
            <dl className="system-state-facts">
              {detail.facts.map((fact) => (
                <div key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          </aside>
        </article>
      </div>
    </div>
  );
}
