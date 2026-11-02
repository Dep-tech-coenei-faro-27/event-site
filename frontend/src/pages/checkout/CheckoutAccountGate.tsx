import { Link } from "react-router-dom";

/** «Antes de comprar, cria a tua conta» (`ui-ux/bilhetes/checkout/conta`): quem não tem sessão não vê o formulário. */
export default function CheckoutAccountGate() {
  return (
    <div className="auth-page">
      <section className="auth-section">
        <div className="container auth-shell">
          <aside className="auth-aside">
            <div>
              <p className="eyebrow">&lt;COMPRA /&gt;</p>
              <h1>O bilhete fica na tua conta.</h1>
              <p className="lead">
                Cria uma conta ou entra para comprares o bilhete.
              </p>
            </div>
            <div className="auth-points">
              {[
                "Cria a tua conta ou inicia sessão.",
                "Escolhe a modalidade do bilhete.",
                "Conclui o pagamento por MB WAY.",
                "Consulta o bilhete na tua área pessoal.",
              ].map((text, index) => (
                <div className="auth-point" key={text}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <p>{text}</p>
                </div>
              ))}
            </div>
          </aside>
          <div className="auth-card">
            <div className="auth-state-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="8" r="4"></circle>
                <path d="M4 21a8 8 0 0 1 16 0M18 8h4M20 6v4"></path>
              </svg>
            </div>
            <p className="eyebrow">&lt;CONTA_NECESSÁRIA /&gt;</p>
            <h2>Vamos guardar o teu bilhete.</h2>
            <p className="auth-intro">
              Entra ou cria uma conta para continuar.
            </p>
            <div className="auth-actions">
              <Link className="btn btn--primary" to="/conta/criar">
                Criar conta
              </Link>
              <Link className="btn btn--secondary" to="/conta">
                Já tenho conta
              </Link>
            </div>
            <p className="auth-switch">
              <Link className="auth-back" to="/bilhetes">
                ← Voltar aos bilhetes
              </Link>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
