import "../parcerias.css";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";

/** `ui-ux/parcerias/index.html` no React. CSS gerado em `parcerias.css` (ver `scripts/ui-port/genpage.py`). */
export default function Parcerias() {
  useBodyPage("parcerias");
  usePageMeta('Parcerias · ENEI 2027', 'Parcerias e oportunidades de patrocínio no ENEI 2027.');

  return (
    <>

      <header className="page-hero page-hero--image center">
      <div className="container">
      <p className="eyebrow">&lt;PARCERIAS /&gt;</p>
      <h1>Contacta com as melhores empresas de tecnologia.</h1>
      <p className="lead">
      Uma plataforma nacional para aproximar talento, conhecimento e
      organizações que estão a construir o futuro.
      </p>
      <div className="actions" style={{ justifyContent: "center" }}>
      <a href="#contacto" className="btn btn--primary">Tornar-me parceiro</a><a href="#niveis" className="btn btn--secondary">Ver níveis</a>
      </div>
      </div>
      </header>
      <section className="section">
      <div className="container center">
      <p className="eyebrow">&lt;VALOR /&gt;</p>
      <h2>Porquê ser parceiro do ENEI 2027?</h2>
      <div className="benefit-grid" style={{ marginTop: "42px", textAlign: "left" }}>
      <article className="benefit-item">
      <div className="icon icon--teal" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <circle cx="9" cy="8" r="3" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0M14 15.5a4.5 4.5 0 0 1 6.5 4" />
      </svg>
      </div>
      <h3>Acesso ao talento</h3>
      <p>
      Contacto direto com estudantes de informática de todo o país.
      </p>
      </article>
      <article className="benefit-item">
      <div className="icon icon--sand" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6z" />
      <circle cx="12" cy="12" r="2.7" />
      </svg>
      </div>
      <h3>Visibilidade</h3>
      <p>Presença integrada antes, durante e depois do evento.</p>
      </article>
      <article className="benefit-item">
      <div className="icon icon--periwinkle" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <circle cx="9" cy="8" r="3" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0M14 15.5a4.5 4.5 0 0 1 6.5 4" />
      </svg>
      </div>
      <h3>Networking</h3>
      <p>Relações com academia, comunidades e outras empresas.</p>
      </article>
      <article className="benefit-item">
      <div className="icon icon--coral" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" />
      <path d="M17 7l4-4M17 3h4v4" />
      </svg>
      </div>
      <h3>Impacto</h3>
      <p>
      Apoio concreto ao desenvolvimento da comunidade tecnológica.
      </p>
      </article>
      </div>
      </div>
      </section>
      <section className="section section--surface" id="niveis">
      <div className="container">
      <div className="center">
      <p className="eyebrow">&lt;PATROCÍNIO /&gt;</p>
      <h2>Níveis de parceria</h2>
      <p className="lead">
      Escolhe o nível de presença que melhor acompanha os objetivos da
      tua organização.
      </p>
      </div>
      <div style={{ marginTop: "46px" }}>
      <div className="tier">
      <strong>Diamante</strong>
      <div>
      <h3>Presença principal</h3>
      <ul>
      <li>Ativação de marca</li>
      <li>Espaço de exposição</li>
      <li>Participação no programa</li>
      <li>Comunicação premium</li>
      </ul>
      </div>
      </div>
      <div className="tier">
      <strong style={{ color: "#f4c542" }}>Ouro</strong>
      <div>
      <h3>Grande visibilidade</h3>
      <ul>
      <li>Espaço de exposição</li>
      <li>Presença editorial</li>
      <li>Atividades com participantes</li>
      <li>Marca em suportes</li>
      </ul>
      </div>
      </div>
      <div className="tier">
      <strong style={{ color: "#c8d0da" }}>Prata</strong>
      <div>
      <h3>Ligação à comunidade</h3>
      <ul>
      <li>Presença de marca</li>
      <li>Divulgação digital</li>
      <li>Acesso ao evento</li>
      <li>Networking</li>
      </ul>
      </div>
      </div>
      <div className="tier">
      <strong style={{ color: "#d18b53" }}>Bronze</strong>
      <div>
      <h3>Apoio ao encontro</h3>
      <ul>
      <li>Logótipo no site</li>
      <li>Menção institucional</li>
      <li>Acesso ao evento</li>
      <li>Comunidade</li>
      </ul>
      </div>
      </div>
      </div>
      </div>
      </section>
      <section className="section section--surface">
      <div className="container center">
      <p className="eyebrow">&lt;REDE DE APOIO /&gt;</p>
      <h2>Uma rede que apoia o ENEI</h2>
      <p className="lead">
      Instituições académicas, autarquias e organizações tecnológicas
      unidas à comunidade ENEI.
      </p>
      <div className="logo-grid" style={{ marginTop: "40px" }}>
      <div className="logo-placeholder">UAlg</div>
      <div className="logo-placeholder">FCT UAlg</div>
      <div className="logo-placeholder">AAUAlg</div>
      <div className="logo-placeholder">NEEC</div>
      <div className="logo-placeholder">Algarve Evolution</div>
      <div className="logo-placeholder">UAlg Cria</div>
      <div className="logo-placeholder">CM Faro</div>
      <div className="logo-placeholder">CM Loulé</div>
      <div className="logo-placeholder">CM Portimão</div>
      <div className="logo-placeholder">CM Lagos</div>
      <div className="logo-placeholder">CM Aljustrel</div>
      <div className="logo-placeholder">CM São Brás</div>
      <div className="logo-placeholder">Tomás Cabreira</div>
      </div>
      </div>
      </section>
      <section className="section section--surface" id="contacto">
      <div className="container">
      <div className="cta center">
      <h2>Torna-te parceiro do ENEI 2027.</h2>
      <p style={{ marginInline: "auto" }}>
      Solicita o dossier comercial e conversa com a equipa de parcerias.
      </p>
      <div className="actions" style={{ justifyContent: "center" }}>
      <a href="mailto:parcerias@enei.pt" className="btn btn--dark">Contactar parcerias</a>
      </div>
      </div>
      </div>
      </section>

    </>
  );
}
