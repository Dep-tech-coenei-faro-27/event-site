import { Link } from "react-router-dom";
import "../bilhetes.css";
import "../bilhetes.overrides.css";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";
import { EarlyBirdNotice, TicketPrice } from "./bilhetes/TicketPrice";
import { useTierPrices } from "./bilhetes/useTierPrices";

/** `ui-ux/bilhetes/index.html` no React. CSS gerado em `bilhetes.css` (ver `scripts/ui-port/genpage.py`). */
export default function Bilhetes() {
  useBodyPage("bilhetes");
  usePageMeta('Bilhetes · ENEI 2027', 'Bilhetes e preparação para o ENEI 2027.');
  const prices = useTierPrices();

  return (
    <>

      <header className="page-hero">
      <div className="container">
      <p className="eyebrow">&lt;BILHETES /&gt;</p>
      <h1>O teu lugar no ENEI.</h1>
      <p className="lead">
      Compara os bilhetes e escolhe o que queres incluir.
      </p>
      <div className="actions">
      <a href="#tipos" className="btn btn--secondary">Ver modalidades</a><Link to="/bilhetes/checkout" className="btn btn--primary">Comprar bilhete</Link>
      </div>
      </div>
      </header>
      <section className="section section--surface" id="tipos">
      <div className="container">
      <p className="eyebrow">&lt;MODALIDADES /&gt;</p>
      <h2>O que queres incluir?</h2>
      <p className="lead">
      Só o evento, refeições ou também alojamento. A escolha é tua.
      </p>
      <EarlyBirdNotice prices={prices} />
      <div className="grid grid--4" style={{ marginTop: "42px" }}>
      <article className="ticket-card">
      <p className="eyebrow">ESTUDANTE</p>
      <h3>Apenas acesso</h3>
      <TicketPrice prices={prices} slug="acesso" />
      <ul className="feature-list">
      <li>Entrada no evento</li>
      <li>Programa geral</li>
      <li>Sem refeições ou estadia</li>
      </ul>
      <Link to="/bilhetes/checkout?bilhete=acesso" className="btn btn--secondary">
      Escolher bilhete
      </Link>
      </article>
      <article className="ticket-card">
      <p className="eyebrow">ESTUDANTE</p>
      <h3>Acesso + refeições</h3>
      <TicketPrice prices={prices} slug="refeicoes" />
      <ul className="feature-list">
      <li>Entrada no evento</li>
      <li>Refeições incluídas</li>
      <li>Sem estadia</li>
      </ul>
      <Link to="/bilhetes/checkout?bilhete=refeicoes" className="btn btn--secondary">
      Escolher bilhete
      </Link>
      </article>
      <article className="ticket-card ticket-card--featured">
      <span className="ticket-badge">Recomendado</span>
      <p className="eyebrow">ESTUDANTE</p>
      <h3>Experiência completa</h3>
      <TicketPrice prices={prices} slug="completo" />
      <ul className="feature-list">
      <li>Entrada no evento</li>
      <li>Refeições incluídas</li>
      <li>Alojamento coletivo</li>
      </ul>
      <Link to="/bilhetes/checkout?bilhete=completo" className="btn btn--secondary">
      Escolher bilhete
      </Link>
      </article>
      <article className="ticket-card">
      <p className="eyebrow">NÃO ESTUDANTE</p>
      <h3>Passe geral</h3>
      <TicketPrice prices={prices} slug="geral" />
      <ul className="feature-list">
      <li>Entrada no evento</li>
      <li>Programa geral</li>
      <li>Sem refeições ou estadia</li>
      </ul>
      <Link to="/bilhetes/checkout?bilhete=geral" className="btn btn--secondary">
      Escolher bilhete
      </Link>
      </article>
      <article className="ticket-card">
      <p className="eyebrow">NÃO ESTUDANTE</p>
      <h3>Passe geral + refeições</h3>
      <TicketPrice prices={prices} slug="geral_refeicoes" />
      <ul className="feature-list">
      <li>Acesso ao programa completo</li>
      <li>Refeições incluídas</li>
      <li>Sem estadia</li>
      </ul>
      <Link to="/bilhetes/checkout?bilhete=geral_refeicoes" className="btn btn--secondary">
      Escolher bilhete
      </Link>
      </article>
      </div>
      </div>
      </section>
      <section className="section">
      <div className="container">
      <p className="eyebrow">&lt;INSCRIÇÃO /&gt;</p>
      <h2>Prepara a tua inscrição</h2>
      <p className="lead">
      Tem os teus dados e, se fores estudante, um comprovativo à mão.
      </p>
      <div className="registration-prep">
      <article className="checklist-column">
      <svg className="registration-prep__icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><circle cx="12" cy="7.5" r="4.5"/><path d="M3 20a9 9 0 0 1 18 0v1H3z"/></svg>
      <h3>Dados pessoais</h3>
      <div className="registration-prep__content">
      <ul className="feature-list">
      <li>Nome completo</li>
      <li>Email</li>
      <li>Contacto</li>
      </ul>
      </div>
      </article>
      <article className="checklist-column checklist-column--notice">
      <svg className="registration-prep__icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><path fillRule="evenodd" d="M4 4h16a2 2 0 0 1 2 2v3a3 3 0 0 0 0 6v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a3 3 0 0 0 0-6V6a2 2 0 0 1 2-2Zm10 2v3h2V6h-2Zm0 5v2h2v-2h-2Zm0 4v3h2v-3h-2Z" clipRule="evenodd"/></svg>
      <h3>O bilhete fica na tua conta</h3>
      <div className="registration-prep__content">
      <p>
      Compra aqui e consulta o bilhete na área pessoal.
      </p>
      <p>
      Dúvidas? Escreve para <a href="mailto:geral@eneiconf.pt">geral@eneiconf.pt</a>.
      </p>
      </div>
      </article>
      <article className="checklist-column checklist-column--proof">
      <svg className="registration-prep__icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><path d="m12 3 12 6-12 6L0 9l12-6Zm-7 10.5 7 3.5 7-3.5V18c-4.2 3.2-9.8 3.2-14 0v-4.5ZM22 12l2-1v8h-2v-7Z"/></svg>
      <h3>Bilhete de estudante</h3>
      <div className="registration-prep__content">
      <p>
      Comprova que és estudante com a matrícula, o cartão de estudante ou outro documento da tua instituição.
      </p>
      <p>
      Envia o comprovativo na área pessoal. Precisas de ajuda? <a href="mailto:geral@eneiconf.pt">geral@eneiconf.pt</a>.
      </p>
      </div>
      </article>
      </div>
      </div>
      </section>
      <section className="section section--panel">
      <div className="container split">
      <div>
      <p className="eyebrow">&lt;PROCESSO /&gt;</p>
      <h2>O teu bilhete em três passos.</h2>
      <p className="lead">
      O bilhete fica na tua área pessoal.
      </p>
      </div>
      <div className="timeline">
      <div className="timeline-item">
      <small>PASSO 01</small>
      <h3>Compara</h3>
      <p>Escolhe o que queres incluir.</p>
      </div>
      <div className="timeline-item">
      <small>PASSO 02</small>
      <h3>Compra</h3>
      <p>
      Confirma os dados e conclui o pagamento.
      </p>
      </div>
      <div className="timeline-item">
      <small>PASSO 03</small>
      <h3>Acompanha</h3>
      <p>Consulta o bilhete na tua conta.</p>
      </div>
      </div>
      </div>
      </section>
      <section className="section">
      <div className="container">
      <div className="cta ticket-help">
      <div className="ticket-help__copy">
      <h2>Precisas de ajuda?</h2>
      <p>
      Vê as respostas sobre bilhetes, estadia e transportes.
      </p>
      <div className="actions">
      <Link to="/informacao-ajuda" className="btn btn--dark">Informações e ajuda</Link>
      <a href="mailto:geral@eneiconf.pt" className="btn btn--secondary">Contactar a equipa</a>
      </div>
      </div>
      <svg className="ticket-help__illustration" viewBox="0 0 280 240" aria-hidden="true" focusable="false">
        <path d="M115 24h120a20 20 0 0 1 20 20v66a20 20 0 0 1-20 20h-16l-28 24v-24h-76a20 20 0 0 1-20-20V44a20 20 0 0 1 20-20Z" fill="rgba(255,255,255,.08)" stroke="currentColor" strokeWidth="4" strokeLinejoin="round" />
        <circle cx="147" cy="76" r="5" fill="currentColor" /><circle cx="175" cy="76" r="5" fill="currentColor" /><circle cx="203" cy="76" r="5" fill="currentColor" />
        <path d="M42 88h128a22 22 0 0 1 22 22v68a22 22 0 0 1-22 22H88l-32 27v-27H42a22 22 0 0 1-22-22v-68a22 22 0 0 1 22-22Z" fill="#087eae" stroke="currentColor" strokeWidth="4" strokeLinejoin="round" />
        <path d="M91 126a17 17 0 0 1 32 8c0 12-17 13-17 25" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" />
        <circle cx="106" cy="177" r="3.5" fill="currentColor" />
      </svg>
      </div>
      </div>
      </section>

    </>
  );
}
