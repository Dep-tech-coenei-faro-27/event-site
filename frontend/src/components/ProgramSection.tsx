import { Link } from 'react-router-dom';
import talks from '../assets/about-talks.webp';
import practical from '../assets/about-workshop.webp';
import people from '../assets/about-companies.webp';
import PreviewPhoto from './PreviewPhoto';

const items = [
  { title: 'Aprende com quem faz.', text: 'Ouve, pergunta e descobre novas ideias.', label: 'Palestras', image: talks, alt: 'Apresentação no Vibathon 2026 com participantes a acompanhar a sessão' },
  { title: 'Põe mãos à obra.', text: 'Sessões práticas para experimentar e aprender.', label: 'Workshops', image: practical, alt: 'Participantes numa sessão prática' },
  { title: 'Conhece a comunidade.', text: 'Conhece estudantes e conversa com empresas.', label: 'Encontros', image: people, alt: 'Participantes do Vibathon 2026 a conversar e a trabalhar em grupo, vistos através de uma parede de vidro' },
];

export default function ProgramSection() {
  return (
    <section className="section home-programme azulejo-bg">
      <div className="container">
        <div className="section-heading">
          <div><p className="eyebrow">&lt;PROGRAMA /&gt;</p><h2>O que te espera.</h2></div>
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
