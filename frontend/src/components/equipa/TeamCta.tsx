import { Link } from "react-router-dom";

/** Fecho da página Equipa (`ui-ux/equipa`). */
export default function TeamCta() {
  return (
    <section className="section section--surface">
      <div className="container">
        <div className="cta">
          <p className="eyebrow" style={{ color: "white" }}>
            &lt;COMUNIDADE /&gt;
          </p>
          <h2>Uma equipa aberta ao ecossistema.</h2>
          <p>
            A organização trabalha com a Universidade do Algarve, associações académicas, entidades públicas, comunidades
            e empresas.
          </p>
          <div className="actions">
            <a className="btn btn--dark" href="mailto:equipa@enei.pt">
              Contactar a equipa
            </a>
            <Link className="btn btn--secondary" to="/parcerias">
              Conhecer parcerias
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
