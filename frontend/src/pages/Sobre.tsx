import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import participants from '../assets/agenda-auditorio.webp';
import eneiSymbol from '../assets/ENEI-logo.svg';
import faroEvening from '../assets/faro-baixa.webp';
import campus from '../assets/ualg-estudantes-biblioteca.webp';
import { AGENDA } from '../content/agenda';
import { useBodyPage } from '../utils/useBodyPage';
import { usePageMeta } from '../utils/usePageMeta';
import '../sobre.css';
import '../sobre-reading.css';

const icons = {
  talks: <><path d="M8 3h8v9a4 4 0 0 1-8 0V3Z" /><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8" /></>,
  practical: <><path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18" /></>,
  people: <><circle cx="9" cy="7" r="3" /><path d="M3 21v-3a6 6 0 0 1 12 0v3M17 4a3 3 0 0 1 0 6m2 4a5 5 0 0 1 2 4v3" /></>,
  location: <><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  stay: <><path d="m3 10 9-7 9 7v11H3V10Z" /><path d="M9 21v-8h6v8" /></>,
  ticket: <><path d="M3 6h18v4a2 2 0 0 0 0 4v4H3v-4a2 2 0 0 0 0-4V6Z" /><path d="M15 6v3m0 3v1m0 3v2" /></>,
};

function AboutIcon({ name }: { name: keyof typeof icons }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name]}</svg>;
}

const experiences = [
  { icon: 'talks', title: 'Ouve novas ideias.', label: 'Palestras', text: 'Conhece diferentes áreas da informática e aprende com quem trabalha no setor.' },
  { icon: 'practical', title: 'Põe mãos à obra.', label: 'Sessões práticas e desafios', text: 'Experimenta ferramentas, resolve problemas e cria em equipa.' },
  { icon: 'people', title: 'Encontra a tua comunidade.', label: 'Convívio e oportunidades', text: 'Troca ideias com estudantes de todo o país e conhece quem trabalha nas empresas.' },
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
        <p className="eyebrow">Sobre o encontro</p>
        <h1>O ENEI vem a Faro.</h1>
        <p className="lead">Quatro dias de tecnologia, partilha e convívio. De 1 a 4 de abril de 2027, encontramo-nos no Algarve.</p>
      </div></header>

      <section className="section section--compact section--surface about-highlights" aria-label="O ENEI em resumo"><div className="container">
        <div className="fact-grid azulejo-bg">
          <div className="fact"><small>Edição</small><strong>18.ª</strong><span>Encontro nacional</span></div>
          <div className="fact"><small>Quando</small><strong>4 dias</strong><span>1 a 4 de abril de 2027</span></div>
          <div className="fact"><small>Programa</small><strong>{count}</strong><span>Atividades previstas</span></div>
          <div className="fact"><small>Onde</small><strong>Faro</strong><span>Campus das Gambelas</span></div>
        </div>
      </div></section>

      <section className="section about-block about-intro azulejo-bg" aria-labelledby="about-essential-title"><div className="container about-intro__layout">
        <div>
          <p className="eyebrow">O encontro</p>
          <h2 id="about-essential-title">O que é o ENEI?</h2>
          <p className="about-intro__lead">O Encontro Nacional de Estudantes de Informática junta a comunidade académica e o setor tecnológico para aprender, experimentar e criar ligações.</p>
          <div className="about-audience">
            <AboutIcon name="people" />
            <div><h3>Há lugar para ti.</h3><p>Estudantes, profissionais e todas as pessoas com curiosidade por tecnologia.</p></div>
          </div>
          <More title="Mais sobre o encontro">
            <p>No ENEI, encontras estudantes, comunidades, instituições e empresas de todo o país. São quatro dias de palestras, sessões práticas, desafios e convívio que ligam a vida académica ao mundo do trabalho.</p>
            <p>Vem conhecer outras perspetivas, experimentar ferramentas e trocar ideias com quem estuda e trabalha na área. Se estudas informática ou uma área próxima, já trabalhas no setor ou tens curiosidade por tecnologia, há lugar para ti.</p>
          </More>
        </div>
        <figure className="about-intro__photo">
          <img src={participants} alt="Participantes a assistir a uma sessão num auditório" width={1024} height={768} loading="lazy" />
          <figcaption>Conhecimento que se partilha.</figcaption>
        </figure>
      </div></section>

      <section className="section about-block about-experience" aria-labelledby="about-programme-title"><div className="container">
        <div className="about-section-heading"><div><p className="eyebrow">A experiência ENEI</p><h2 id="about-programme-title">O que vais encontrar.</h2></div><Link className="about-text-link" to="/agenda"><span className="about-link-label">Explora a agenda</span><span className="about-link-arrow" aria-hidden="true">→</span></Link></div>
        <div className="about-experience__tiles">
          {experiences.map(item => <article className="about-tile azulejo-bg" key={item.icon}>
            <AboutIcon name={item.icon} /><p className="about-tile__label">{item.label}</p><h3>{item.title}</h3><p>{item.text}</p>
          </article>)}
        </div>
        <More title="Mais sobre as atividades">
          <p><strong>Palestras e sessões práticas.</strong> Descobre diferentes áreas da informática e ouve as experiências de quem trabalha no setor. Nas sessões práticas, experimenta ferramentas e põe em prática o que aprendeste.</p>
          <p><strong>Desafios e colaboração.</strong> Resolve problemas, trabalha em equipa e põe a tua criatividade à prova com pessoas que trazem experiências e conhecimentos diferentes.</p>
          <p><strong>Comunidade e oportunidades.</strong> Conhece estudantes de outras instituições e profissionais do setor. Entre conversas e convívio, faz novos contactos e descobre oportunidades na área da tecnologia.</p>
        </More>
      </div></section>

      <section className="section about-block about-makers" aria-labelledby="about-community-title"><div className="container about-makers__layout">
        <figure className="about-makers__photo"><img src={campus} alt="Estudantes junto à Biblioteca da Universidade do Algarve, no Campus das Gambelas" width={1800} height={1198} loading="lazy" /><figcaption>Vida no campus · Fotografia: UAlg</figcaption></figure>
        <div className="about-makers__copy azulejo-bg">
          <p className="eyebrow">A organização</p><h2 id="about-community-title">Feito por estudantes.</h2>
          <p>Uma equipa do NEEI da Universidade do Algarve prepara a edição de Faro para receber participantes de todo o país.</p>
          <More title="Saber mais sobre a organização">
            <p>A edição de Faro é organizada pelo Núcleo de Estudantes de Engenharia Informática (NEEI) da Universidade do Algarve. Os vários departamentos da equipa tratam do programa, da comunicação, da logística e de tudo o que faz o encontro acontecer.</p>
            <p>Ao longo do ano, o NEEI liga os estudantes à comunidade académica e às empresas, com atividades e voluntariado na região. Com o ENEI, essa ligação chega a todo o país.</p>
          </More>
          <Link className="about-text-link" to="/equipa"><span className="about-link-label">Conhece a equipa</span><span className="about-link-arrow" aria-hidden="true">→</span></Link>
        </div>
      </div></section>

      <section className="section about-block about-faro azulejo-bg" id="faro" aria-labelledby="about-city-title"><div className="container">
        <div className="about-faro__banner">
          <img src={faroEvening} alt="Cais na Baixa de Faro ao fim do dia" width={1500} height={1000} loading="lazy" />
          <div className="about-faro__copy"><p className="eyebrow">Baixa de Faro · Cais</p><h2 id="about-city-title">A tecnologia encontra<br />o Algarve.</h2><p>Vida académica, património e a Ria Formosa. Uma cidade para descobrires entre atividades.</p><ul aria-label="Descobrir Faro"><li>Centro histórico</li><li>Ria Formosa</li><li>Comunidade académica</li></ul></div>
        </div>
        <More title="Mais sobre Faro e os acessos">
          <p>Faro junta vida académica, património e a proximidade da Ria Formosa. Em 2027, a Universidade do Algarve e a comunidade tecnológica da região recebem o encontro.</p>
          <p>Podes chegar de comboio, autocarro ou avião. Entre atividades, aproveita para explorar o centro histórico e passear junto à ria.</p>
        </More>
      </div></section>

      <section className="section about-block about-practical" aria-labelledby="about-visit-title"><div className="container"><div className="about-practical__panel azulejo-bg"><img className="about-practical__symbol" src={eneiSymbol} alt="" aria-hidden="true" />
        <div className="about-section-heading"><div><p className="eyebrow">Informação prática</p><h2 id="about-visit-title">Prepara os quatro dias.</h2></div></div>
        <div className="about-practical__tiles">
          <Link className="about-practical-tile" to="/informacao-ajuda#localizacoes"><AboutIcon name="location" /><div><h3>Locais e acessos</h3><p>As atividades principais decorrem no Campus das Gambelas.</p><span><span className="about-link-label">Prepara a viagem</span><span className="about-link-arrow" aria-hidden="true">→</span></span></div></Link>
          <Link className="about-practical-tile" to="/bilhetes"><AboutIcon name="stay" /><div><h3>Alojamento e refeições</h3><p>Descobre o que cada bilhete inclui em alojamento e refeições.</p><span><span className="about-link-label">Compara os bilhetes</span><span className="about-link-arrow" aria-hidden="true">→</span></span></div></Link>
          <Link className="about-practical-tile" to="/conta"><AboutIcon name="ticket" /><div><h3>O teu bilhete</h3><p>Depois da inscrição, acede ao bilhete na tua área pessoal.</p><span><span className="about-link-label">Entra na tua conta</span><span className="about-link-arrow" aria-hidden="true">→</span></span></div></Link>
        </div>
      </div></div></section>
    </>
  );
}
