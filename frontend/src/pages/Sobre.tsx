import { Link } from "react-router-dom";
import about_companies from "../assets/about-companies.webp";
import about_talks from "../assets/about-talks.webp";
import about_workshop from "../assets/about-workshop.webp";
import faro_baixa from "../assets/faro-baixa.webp";
import gambelas from "../assets/gambelas.webp";
import "../sobre.css";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";

/** `ui-ux/sobre/index.html` no React. CSS gerado em `sobre.css` (ver `scripts/ui-port/genpage.py`). */
export default function Sobre() {
  useBodyPage("sobre");
  usePageMeta('Sobre · ENEI 2027', 'Conhece a história, os pilares e a cidade anfitriã do ENEI 2027.');

  return (
    <>

      <header className="page-hero">
      <div className="container">
      <p className="eyebrow">&lt;SOBRE /&gt;</p>
      <h1>O que é o ENEI?</h1>
      <p className="lead">
      O Encontro Nacional de Estudantes de Informática reúne estudantes,
      comunidades, instituições e empresas numa experiência criada para
      aprender, partilhar e construir ligações.
      </p>
      </div>
      </header>
      <section className="section section--compact section--surface">
      <div className="container photo-gallery">
      <figure>
      <img src={about_talks} alt="Palestra num auditório do ENEI" />
      </figure>
      <figure>
      <img src={about_workshop} alt="Participantes num workshop técnico" />
      </figure>
      <figure>
      <img src={about_companies} alt="Área de empresas e networking" />
      </figure>
      </div>
      </section>
      <section className="section">
      <div className="container split">
      <div>
      <p className="eyebrow">&lt;HISTÓRIA /&gt;</p>
      <h2>Uma história de inovação.</h2>
      <p className="lead">
      Uma iniciativa estudantil que atravessa gerações e continua a
      aproximar o ensino superior do ecossistema tecnológico nacional.
      </p>
      </div>
      <div className="timeline">
      <div className="timeline-item">
      <small>ORIGEM</small>
      <h3>Uma comunidade nacional</h3>
      <p>
      Estudantes de informática juntam-se para trocar conhecimento e
      experiências.
      </p>
      </div>
      <div className="timeline-item">
      <small>EVOLUÇÃO</small>
      <h3>Mais formatos, mais ligações</h3>
      <p>
      O encontro cresce com workshops, palestras, desafios e contacto
      empresarial.
      </p>
      </div>
      <div className="timeline-item">
      <small>2027</small>
      <h3>O ENEI chega a Faro</h3>
      <p>
      Uma nova edição, preparada pela comunidade académica do Algarve.
      </p>
      </div>
      </div>
      </div>
      </section>
      <section className="section section--surface">
      <div className="container">
      <p className="eyebrow">&lt;CONTEXTO /&gt;</p>
      <h2>Academia, região e tecnologia.</h2>
      <div className="fact-grid">
      <div className="fact">
      <strong>18.ª</strong><span>Edição nacional realizada em Faro.</span>
      </div>
      <div className="fact">
      <strong>4 dias</strong><span>Conhecimento, networking e comunidade.</span>
      </div>
      <div className="fact">
      <strong>≈10 mil</strong><span>Estudantes na Universidade do Algarve.</span>
      </div>
      <div className="fact">
      <strong>300+</strong><span>Dias de sol por ano na região.</span>
      </div>
      </div>
      </div>
      </section>
      <section className="section section--panel">
      <div className="container center">
      <p className="eyebrow">&lt;VALORES /&gt;</p>
      <h2>Os nossos pilares</h2>
      <div className="pillar-list" style={{ marginTop: "42px", textAlign: "left" }}>
      <article className="pillar-item">
      <div className="icon icon--teal" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5z" />
      <path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5z" />
      </svg>
      </div>
      <h3>Conhecimento</h3>
      <p>
      Aprender com especialistas, experimentar novas ferramentas e
      descobrir caminhos profissionais.
      </p>
      </article>
      <article className="pillar-item">
      <div className="icon icon--periwinkle" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <circle cx="9" cy="8" r="3" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0M14 15.5a4.5 4.5 0 0 1 6.5 4" />
      </svg>
      </div>
      <h3>Networking</h3>
      <p>
      Criar relações genuínas entre estudantes, comunidades, academia
      e indústria.
      </p>
      </article>
      <article className="pillar-item">
      <div className="icon icon--teal" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="M12 3 5 6v5c0 4.7 2.9 8.1 7 10 4.1-1.9 7-5.3 7-10V6z" />
      <path d="m9 12 2 2 4-4" />
      </svg>
      </div>
      <h3>Cidadania</h3>
      <p>
      Construir uma comunidade tecnológica mais responsável, diversa e
      participativa.
      </p>
      </article>
      </div>
      </div>
      </section>
      <section className="section" id="faro">
      <div className="container split">
      <div className="photo">
      <img src={faro_baixa} alt="Marina e centro histórico de Faro" />
      </div>
      <div>
      <p className="eyebrow">&lt;LOCALIZAÇÃO /&gt;</p>
      <h2>Porquê Faro?</h2>
      <p className="lead">
      Capital do Algarve, Faro cruza património histórico, a Ria Formosa
      e um ecossistema tecnológico em crescimento.
      </p>
      <ul className="feature-list">
      <li>
      Universidade do Algarve e comunidade académica internacional
      </li>
      <li>Algarve Tech Hub, startups e empresas tecnológicas</li>
      <li>Acessos ferroviários, rodoviários e aéreos</li>
      <li>Cidade compacta, património e natureza</li>
      </ul>
      </div>
      </div>
      </section>
      <section className="section section--surface">
      <div className="container split">
      <div>
      <p className="eyebrow">&lt;UALG + NEEI /&gt;</p>
      <h2>Uma comunidade que transforma teoria em prática.</h2>
      <p className="lead">
      O NEEI aproxima estudantes do tecido empresarial através de
      atividades, voluntariado e participação ativa no ecossistema
      tecnológico algarvio.
      </p>
      <div className="reference-projects" style={{ marginTop: "32px" }}>
      <article className="reference-project">
      <h3>Algarve Summit</h3>
      <p>
      Palestras, workshops e painéis que ligam academia,
      investigação e empresas da região.
      </p>
      </article>
      <article className="reference-project">
      <h3>GDG Buildathon</h3>
      <p>
      Maratona de desenvolvimento orientada à colaboração,
      pensamento crítico e criação tecnológica.
      </p>
      </article>
      </div>
      </div>
      <div className="photo campus-photo">
      <img src={gambelas} alt="Campus das Gambelas da Universidade do Algarve" />
      </div>
      </div>
      </section>
      <section className="section section--surface">
      <div className="container">
      <div className="section-heading">
      <div>
      <p className="eyebrow">&lt;ORGANIZAÇÃO /&gt;</p>
      <h2>Quem organiza o ENEI 2027?</h2>
      </div>
      <p className="lead">
      Uma equipa multidisciplinar de estudantes, apoiada por estruturas
      académicas e parceiros.
      </p>
      </div>
      <div className="department-strip">
      <div className="department-strip__item">
      <div className="icon icon--periwinkle" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="9" />
      <path d="m15.5 8.5-2 5-5 2 2-5z" />
      </svg>
      </div>
      <h3>Coordenação</h3>
      <p>Estratégia e articulação geral.</p>
      </div>
      <div className="department-strip__item">
      <div className="icon icon--sand" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <rect x="3" y="5" width={18} height={16} rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18M8 14h3M8 17h6" />
      </svg>
      </div>
      <h3>Programa</h3>
      <p>Conteúdos e experiências.</p>
      </div>
      <div className="department-strip__item">
      <div className="icon icon--teal" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9" />
      </svg>
      </div>
      <h3>Operações</h3>
      <p>Logística e produção.</p>
      </div>
      <div className="department-strip__item">
      <div className="icon icon--coral" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="M3 11v2a2 2 0 0 0 2 2h2l2 5h3l-2-5 9 3V6L7 9H5a2 2 0 0 0-2 2z" />
      <path d="M19 9a3 3 0 0 1 0 6" />
      </svg>
      </div>
      <h3>Comunicação</h3>
      <p>Marca e comunidade.</p>
      </div>
      </div>
      <div className="actions" style={{ justifyContent: "center" }}>
      <Link to="/equipa" className="btn btn--primary">Conhecer a equipa</Link>
      </div>
      </div>
      </section>
      <section className="section">
      <div className="container">
      <div className="cta">
      <h2>Fica a par de tudo.</h2>
      <p>
      Consulta a agenda, prepara a tua visita e acompanha as inscrições.
      </p>
      <div className="actions">
      <Link to="/agenda" className="btn btn--dark">Explorar agenda</Link><Link to="/bilhetes" className="btn btn--secondary">Comprar bilhete</Link>
      </div>
      </div>
      </div>
      </section>

    </>
  );
}
