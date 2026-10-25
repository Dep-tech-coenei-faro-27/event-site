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
