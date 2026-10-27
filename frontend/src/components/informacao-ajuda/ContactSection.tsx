/** «Ainda tens dúvidas?» (`ui-ux/informacao-ajuda`). */
export default function ContactSection() {
  return (
    <section className="section section--surface">
      <div className="container split">
        <div>
          <p className="eyebrow">&lt;CONTACTO /&gt;</p>
          <h2>Ainda tens dúvidas?</h2>
          <p className="lead">A nossa equipa ajuda-te a encontrar a informação certa.</p>
          <div className="actions">
            <a className="btn btn--secondary" href="mailto:geral@eneiconf.pt">
              Enviar email
            </a>
            <a className="btn btn--primary" href="mailto:geral@eneiconf.pt">
              Contactar
            </a>
          </div>
        </div>
        <aside className="support-panel">
          <h3>Canais de apoio</h3>
          <ul className="feature-list">
            <li>geral@eneiconf.pt</li>
            <li>Faro, Algarve</li>
            <li>Resposta em horário útil</li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
