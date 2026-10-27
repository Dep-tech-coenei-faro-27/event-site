import { Link } from 'react-router-dom';

const paths = [
  {
    number: '01',
    label: 'Estudantes',
    title: 'Vive os quatro dias.',
    text: 'Palestras, atividades, alojamento, refeições e toda a experiência ENEI.',
    linkText: 'Comprar bilhete',
    to: '/bilhetes',
  },
  {
    number: '02',
    label: 'Empresas',
    title: 'Liga-te ao talento.',
    text: 'Participa no ecossistema, apresenta oportunidades e cria relações com a comunidade.',
    linkText: 'Ver parceiros',
    to: '/#parceiros',
  },
  {
    number: '03',
    label: 'Comunidade',
    title: 'Faz parte do encontro.',
    text: 'Conhece a missão, a equipa organizadora e a rede que constrói a edição de Faro.',
    linkText: 'Descobrir o ENEI',
    to: '/sobre',
  },
];

export default function ParticipationSection() {
  return (
    <section className="section section--panel event-pathways">
      <div className="container">
        <div className="section-heading">
          <div>
            <p className="eyebrow">&lt;PARTICIPA /&gt;</p>
            <h2>Um encontro, diferentes percursos.</h2>
          </div>
          <p className="lead">
            Encontra rapidamente a informação certa para a forma como queres participar no ENEI.
          </p>
        </div>
        <div className="pathway-grid">
          {paths.map((item) => (
            <article className="pathway" key={item.number}>
              <span className="pathway__number">{item.number}</span>
              <div>
                <p className="pathway__label">{item.label}</p>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </div>
              <Link to={item.to}>
                {item.linkText}
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  <path d="M4 12 12 4M6 4h6v6" />
                </svg>
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
