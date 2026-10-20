import { Link } from 'react-router-dom';

const points = [
  {
    label: 'Programa',
    title: 'Aprender e experimentar.',
    text: 'Conteúdo técnico, desafios e cultura académica num só encontro.',
  },
  {
    label: 'Rede',
    title: 'Criar ligações reais.',
    text: 'Estudantes, comunidades e organizações lado a lado durante quatro dias.',
  },
  {
    label: 'Edição',
    title: 'Uma identidade algarvia.',
    text: 'O ambiente de Faro dá ritmo e contexto à experiência de 2027.',
  },
];

export default function AboutSection() {
  return (
    <section className="section home-edition">
      <div className="container split">
        <div>
          <p className="eyebrow">&lt;18.ª EDIÇÃO /&gt;</p>
          <h2>O ponto de encontro da próxima geração tecnológica.</h2>
          <p className="lead">
            Quatro dias para ligar estudantes de todo o país às tendências do setor, ao ecossistema
            empresarial e a novas comunidades.
          </p>
          <div className="actions">
            <Link className="btn btn--secondary" to="/sobre">
              Conhecer o ENEI
            </Link>
          </div>
        </div>
        <dl className="editorial-index" aria-label="O ENEI em três pontos">
          {points.map((point) => (
            <div key={point.label}>
              <dt>{point.label}</dt>
              <dd>
                <strong>{point.title}</strong>
                <span>{point.text}</span>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
