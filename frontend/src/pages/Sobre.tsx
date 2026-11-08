import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import participants from '../assets/sobre-encontro.webp';
import faroEvening from '../assets/faro-baixa.webp';
import teamPhoto from '../assets/equipa.webp';
import { AGENDA } from '../content/agenda';
import { useBodyPage } from '../utils/useBodyPage';
import { usePageMeta } from '../utils/usePageMeta';
import '../sobre.css';
import '../sobre-reading.css';

const experiences = [
  { title: 'Ouve novas ideias.', label: 'Palestras', text: 'Conhece diferentes áreas da informática e aprende com quem trabalha no setor.' },
  { title: 'Põe mãos à obra.', label: 'Sessões práticas e desafios', text: 'Experimenta ferramentas, resolve problemas e cria em equipa.' },
  { title: 'Encontra a tua comunidade.', label: 'Convívio e oportunidades', text: 'Troca ideias com estudantes de todo o país e conhece quem trabalha nas empresas.' },
] as const;

function More({ title, children }: { title: string; children: ReactNode }) {
  return <details className="about-disclosure"><summary>{title}<span aria-hidden="true">+</span></summary><div className="about-disclosure__body">{children}</div></details>;
}

export default function Sobre() {
  useBodyPage('sobre');
  usePageMeta('Sobre · ENEI 2027', 'Descobre o ENEI: o encontro, a comunidade, a organização e Faro, a cidade anfitriã de 2027.');

  const count = AGENDA.filter(item => item.visible !== false).length;

  return (
    <>
      <header className="page-hero"><div className="container">
        <p className="eyebrow">&lt;SOBRE /&gt;</p>
        <h1>O ENEI vem a Faro.</h1>
        <p className="lead">Quatro dias de tecnologia, partilha e convívio. De 1 a 4 de abril de 2027, encontramo-nos no Algarve.</p>
      </div></header>

      <section className="section section--surface"><div className="container">
        <p className="eyebrow">&lt;CONTEXTO /&gt;</p>
        <h2>Academia, região e tecnologia.</h2>
        <div className="fact-grid">
          <div className="fact"><strong>18.ª</strong><span>Edição nacional realizada em Faro.</span></div>
          <div className="fact"><strong>4 dias</strong><span>Conhecimento, networking e comunidade.</span></div>
          <div className="fact"><strong>{count}</strong><span>Atividades previstas.</span></div>
          <div className="fact"><strong>300+</strong><span>Dias de sol por ano na região.</span></div>
        </div>
      </div></section>

      <section className="section" aria-labelledby="about-essential-title"><div className="container split">
        <div>
          <p className="eyebrow">&lt;O ENCONTRO /&gt;</p>
          <h2 id="about-essential-title">O que é o ENEI?</h2>
          <p className="lead">O Encontro Nacional de Estudantes de Informática junta a comunidade académica e o setor tecnológico para aprender, experimentar e criar ligações.</p>
          <div className="reference-projects" style={{ marginTop: '32px' }}>
            <article className="reference-project">
              <h3>Há lugar para ti.</h3>
              <p>Estudantes, profissionais e todas as pessoas com curiosidade por tecnologia.</p>
            </article>
          </div>
          <More title="Mais sobre o encontro">
            <p>No ENEI, encontras estudantes, comunidades, instituições e empresas de todo o país. São quatro dias de palestras, sessões práticas, desafios e convívio que ligam a vida académica ao mundo do trabalho.</p>
            <p>Vem conhecer outras perspetivas, experimentar ferramentas e trocar ideias com quem estuda e trabalha na área. Se estudas informática ou uma área próxima, já trabalhas no setor ou tens curiosidade por tecnologia, há lugar para ti.</p>
          </More>
        </div>
        <figure className="about-figure about-figure--encontro">
          <div className="photo"><img src={participants} alt="Participantes no Vibathon 2026 a trabalhar em grupo com computadores portáteis" width={2560} height={1707} loading="lazy" /></div>
          <figcaption>Conhecimento que se partilha.</figcaption>
        </figure>
      </div></section>

      <section className="section" aria-labelledby="about-programme-title"><div className="container">
        <div className="about-section-heading">
          <div><p className="eyebrow">&lt;EXPERIÊNCIA /&gt;</p><h2 id="about-programme-title">O que vais encontrar.</h2></div>
          <Link className="about-text-link" to="/agenda">Explora a agenda <span aria-hidden="true">→</span></Link>
        </div>
        <div className="reference-projects" style={{ marginTop: '32px' }}>
          {experiences.map(item => (
            <article className="reference-project" key={item.label}>
              <h3>{item.title}</h3>
              <div><p className="about-label">{item.label}</p><p>{item.text}</p></div>
            </article>
          ))}
        </div>
        <More title="Mais sobre as atividades">
          <p><strong>Palestras e sessões práticas.</strong> Descobre diferentes áreas da informática e ouve as experiências de quem trabalha no setor. Nas sessões práticas, experimenta ferramentas e põe em prática o que aprendeste.</p>
          <p><strong>Desafios e colaboração.</strong> Resolve problemas, trabalha em equipa e põe a tua criatividade à prova com pessoas que trazem experiências e conhecimentos diferentes.</p>
          <p><strong>Comunidade e oportunidades.</strong> Conhece estudantes de outras instituições e profissionais do setor. Entre conversas e convívio, faz novos contactos e descobre oportunidades na área da tecnologia.</p>
        </More>
      </div></section>

      <section className="section" aria-labelledby="about-community-title"><div className="container split">
        <figure className="about-figure">
          <div className="photo"><img src={teamPhoto} alt="Fotografia de grupo da equipa organizadora do ENEI 2027" width={5826} height={3884} loading="lazy" /></div>
          <figcaption>A equipa do ENEI 2027.</figcaption>
        </figure>
        <div>
          <p className="eyebrow">&lt;UALG + NEEI /&gt;</p>
          <h2 id="about-community-title">Feito por estudantes.</h2>
          <p className="lead">O NEEI da Universidade do Algarve lidera a organização do ENEI em Faro, com uma equipa que reúne membros do núcleo e estudantes de outros cursos.</p>
          <More title="Saber mais sobre a organização">
            <p>A organização é assegurada por membros do Núcleo de Estudantes de Engenharia Informática (NEEI) da Universidade do Algarve e por estudantes de outros cursos que se juntaram à equipa. Distribuídos por vários departamentos, preparam o programa, a comunicação e a logística para receber participantes de todo o país.</p>
            <p>Ao longo do ano, o NEEI liga os estudantes à comunidade académica e às empresas, com atividades e voluntariado na região. Com o ENEI, essa ligação chega a todo o país.</p>
          </More>
          <p><Link className="about-text-link" to="/equipa">Conhece a equipa <span aria-hidden="true">→</span></Link></p>
        </div>
      </div></section>

      <section className="section" id="faro" aria-labelledby="about-city-title"><div className="container split">
        <div>
          <p className="eyebrow">&lt;LOCALIZAÇÃO /&gt;</p>
          <h2 id="about-city-title">A tecnologia encontra o Algarve.</h2>
          <p className="lead">Vida académica, património e a Ria Formosa. Uma cidade para descobrires entre atividades.</p>
          <ul className="feature-list" aria-label="Descobrir Faro">
            <li>Centro histórico</li>
            <li>Ria Formosa</li>
            <li>Comunidade académica</li>
          </ul>
          <More title="Mais sobre Faro e os acessos">
            <p>Faro junta vida académica, património e a proximidade da Ria Formosa. Em 2027, a Universidade do Algarve e a comunidade tecnológica da região recebem o encontro.</p>
            <p>Podes chegar de comboio, autocarro ou avião. Entre atividades, aproveita para explorar o centro histórico e passear junto à ria.</p>
          </More>
        </div>
        <figure className="about-figure">
          <div className="photo"><img src={faroEvening} alt="Cais na Baixa de Faro ao fim do dia" width={1500} height={1000} loading="lazy" /></div>
          <figcaption>Baixa de Faro · Cais</figcaption>
        </figure>
      </div></section>

      <section className="section" aria-labelledby="about-visit-title"><div className="container">
        <div className="cta">
          <h2 id="about-visit-title">Prepara os quatro dias.</h2>
          <p>Consulta os locais, os acessos e as opções de alojamento e refeições.</p>
          <div className="actions">
            <Link className="btn btn--dark" to="/informacao-ajuda">Informações e ajuda</Link>
            <Link className="btn btn--secondary" to="/bilhetes">Ver bilhetes</Link>
          </div>
        </div>
      </div></section>
    </>
  );
}
