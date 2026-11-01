import { Link } from 'react-router-dom';
import participants from '../assets/agenda-auditorio.webp';
import faroEvening from '../assets/faro-baixa.webp';
import { AGENDA } from '../content/agenda';
import { useBodyPage } from '../utils/useBodyPage';
import { usePageMeta } from '../utils/usePageMeta';
import '../sobre.css';

export default function Sobre() {
  useBodyPage('sobre');
  usePageMeta('Sobre · ENEI 2027', 'Quatro dias de palestras, sessões práticas e convívio em Faro.');
  const count = AGENDA.filter(item => item.visible !== false).length;
  return (
    <>
      <header className="page-hero"><div className="container">
        <p className="eyebrow">Sobre o encontro</p>
        <h1>O ENEI vem a Faro.</h1>
        <p className="lead">Estudantes de todo o país, palestras, sessões práticas e convívio. De 1 a 4 de abril de 2027, encontramo-nos no Algarve.</p>
      </div></header>
      <section className="section section--compact section--surface"><div className="container">
        <div className="fact-grid">
          <div className="fact"><strong>18.ª</strong><span>Edição do ENEI</span></div>
          <div className="fact"><strong>4 dias</strong><span>De 1 a 4 de abril de 2027</span></div>
          <div className="fact"><strong>{count}</strong><span>Atividades previstas no programa</span></div>
          <div className="fact"><strong>Faro</strong><span>Campus das Gambelas</span></div>
        </div>
      </div></section>
      <section className="section about-essential" aria-labelledby="about-essential-title"><div className="container about-essential__layout">
        <div className="about-essential__intro">
          <p className="eyebrow">O encontro</p>
          <h2 id="about-essential-title">O que é o ENEI?</h2>
          <p className="lead">O encontro que liga estudantes de informática à comunidade tecnológica.</p>
        </div>
        <figure className="about-essential__photo">
            <img src={participants} alt="Participantes a assistir a uma sessão num auditório" width={1024} height={768} loading="lazy" />
            <figcaption>Conhecimento que se partilha.<small>Imagem provisória</small></figcaption>
          </figure>
        <dl className="about-essential__details">
          <div><dt>Para quem?</dt><dd>Estudantes e não estudantes, de todo o país.</dd></div>
          <div><dt>Feito por estudantes</dt><dd>NEEI da Universidade do Algarve. <Link to="/equipa">Conhece a equipa.</Link></dd></div>
          <div><dt>Tudo à mão</dt><dd>Programa, bilhete e comprovativo de estudante, aqui no site.</dd></div>
        </dl>
      </div></section>
      <section className="section section--surface" id="faro"><div className="container split">
        <div><p className="eyebrow">Antes de vires</p><h2>Prepara os quatro dias.</h2>
          <p className="lead">Consulta os locais, os acessos e as opções de alojamento e refeições.</p>
          <div className="actions"><Link className="btn btn--primary" to="/informacao-ajuda#localizacoes">Informações práticas</Link><Link className="btn btn--secondary" to="/bilhetes">Ver bilhetes</Link></div>
        </div>
        <figure className="about-practical__photo">
          <img src={faroEvening} alt="Marina de Faro ao fim do dia" width={1024} height={682} loading="lazy" />
        </figure>
      </div></section>
    </>
  );
}
