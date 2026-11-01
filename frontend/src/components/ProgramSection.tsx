import { Link } from 'react-router-dom';
import talks from '../assets/about-talks.webp';
import practical from '../assets/about-workshop.webp';
import people from '../assets/about-companies.webp';
import PreviewPhoto from './PreviewPhoto';

const items = [
  { title: 'Aprende com quem faz.', text: 'Ouve, pergunta e descobre novas ideias.', label: 'Palestras', image: talks, alt: 'Auditório com participantes numa palestra' },
  { title: 'Põe mãos à obra.', text: 'Sessões práticas para experimentar e aprender.', label: 'Oficinas', image: practical, alt: 'Participantes numa sessão prática' },
  { title: 'Encontra a tua malta.', text: 'Conhece estudantes e conversa com empresas.', label: 'Encontros', image: people, alt: 'Participantes a conversar numa área de empresas' },
];

export default function ProgramSection() {
  return (
    <section className="section home-programme">
      <div className="container">
        <div className="section-heading">
          <div><p className="eyebrow">Programa</p><h2>O que te espera.</h2></div>
          <Link className="btn btn--secondary" to="/agenda">Ver programa completo</Link>
        </div>
        <div className="home-programme__grid">
          {items.map((item) => (
            <article className="home-programme__item" key={item.label}>
              <PreviewPhoto src={item.image} alt={item.alt} subject={item.label} />
              <h3>{item.title}</h3><p>{item.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
