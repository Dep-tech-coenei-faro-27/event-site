import { Link } from "react-router-dom";
import "../bilhetes.css";
import "../bilhetes.overrides.css";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";

/** `ui-ux/bilhetes/index.html` no React. CSS gerado em `bilhetes.css` (ver `scripts/ui-port/genpage.py`). */
export default function Bilhetes() {
  useBodyPage("bilhetes");
  usePageMeta('Bilhetes · ENEI 2027', 'Bilhetes e preparação para o ENEI 2027.');

  return (
    <>

      <header className="page-hero">
      <div className="container">
      <p className="eyebrow">&lt;BILHETES /&gt;</p>
      <h1>Garante o teu lugar no ENEI 2027.</h1>
      <p className="lead">
      Escolhe a modalidade certa e prepara tudo o que precisas para viver
      o ENEI 2027.
      </p>
      <div className="actions">
      <a href="#tipos" className="btn btn--secondary">Ver modalidades</a><Link to="/bilhetes/checkout" className="btn btn--primary">Comprar bilhete</Link>
      </div>
      </div>
      </header>
      <section className="section section--surface" id="tipos">
      <div className="container">
      <p className="eyebrow">&lt;MODALIDADES /&gt;</p>
      <h2>Escolhe a experiência certa.</h2>
      <p className="lead">
      Cinco formas de participar, desde o acesso ao programa até à
      experiência completa.
      </p>
      <div className="grid grid--4" style={{ marginTop: "42px" }}>
      <article className="ticket-card">
      <p className="eyebrow">ESTUDANTE</p>
      <h3>Apenas acesso</h3>
      <div className="price">Acesso</div>
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
      <div className="price">Acesso + refeições</div>
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
      <div className="price">Experiência completa</div>
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
      <div className="price">Passe geral</div>
      <ul className="feature-list">
      <li>Acesso ao programa</li>
      <li>Programa completo</li>
      <li>Condições dedicadas</li>
      </ul>
      <Link to="/bilhetes/checkout?bilhete=geral" className="btn btn--secondary">
      Escolher bilhete
      </Link>
      </article>
      <article className="ticket-card">
      <p className="eyebrow">NÃO ESTUDANTE</p>
      <h3>Passe geral + refeições</h3>
      <div className="price">Passe geral + refeições</div>
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
      Tem estes elementos contigo para completar o processo de forma
      simples.
      </p>
      <div className="registration-checklist" style={{ marginTop: "38px" }}>
      <article className="checklist-column">
      <h3>Dados pessoais</h3>
      <ul className="feature-list">
      <li>Nome completo</li>
      <li>Email</li>
      <li>Contacto</li>
      </ul>
      </article>
      <article className="checklist-column">
      <h3>Participação</h3>
      <ul className="feature-list">
      <li>Instituição</li>
      <li>Curso</li>
      <li>Necessidades alimentares</li>
      </ul>
      </article>
      <article className="checklist-column checklist-column--notice">
      <h3>Canal oficial</h3>
      <p>
      Usa apenas a área pessoal do ENEI para enviar dados e acompanhar
      o bilhete.
      </p>
      </article>
      </div>
      </div>
      </section>
      <section className="section section--panel">
      <div className="container split">
      <div>
      <p className="eyebrow">&lt;PROCESSO /&gt;</p>
      <h2>Um processo simples</h2>
      <p className="lead">
      Do primeiro passo à chegada ao evento, tudo fica organizado na tua
      conta.
      </p>
      </div>
      <div className="timeline">
      <div className="timeline-item">
      <small>PASSO 01</small>
      <h3>Compara</h3>
      <p>Consulta as modalidades e escolhe a experiência certa.</p>
      </div>
      <div className="timeline-item">
      <small>PASSO 02</small>
      <h3>Compra</h3>
      <p>
      Preenche os teus dados e seleciona as opções da participação.
      </p>
      </div>
      <div className="timeline-item">
      <small>PASSO 03</small>
      <h3>Acompanha</h3>
      <p>Gere o bilhete e a informação do participante na tua conta.</p>
      </div>
      </div>
      </div>
      </section>
      <section className="section section--surface">
      <div className="container center">
      <h2>Precisas de ajuda?</h2>
      <p className="lead">
      Consulta as respostas sobre modalidades, alojamento, transportes e
      participação.
      </p>
      <div className="actions" style={{ justifyContent: "center" }}>
      <Link to="/informacao-ajuda" className="btn btn--primary">Informação &amp; Ajuda</Link>
      </div>
      </div>
      </section>

    </>
  );
}
