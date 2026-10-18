import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

type ProgramItem = {
  title: string;
  text: string;
  tone: 'cyan' | 'coral' | 'periwinkle' | 'sand';
  icon: ReactNode;
};

const items: ProgramItem[] = [
  {
    title: 'Workshops',
    text: 'Sessões práticas em grupos reduzidos.',
    tone: 'cyan',
    icon: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="m7 9 3 3-3 3M13 15h4" />
      </>
    ),
  },
  {
    title: 'Palestras',
    text: 'Ideias e experiências de quem está a construir o futuro.',
    tone: 'coral',
    icon: (
      <>
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8" />
      </>
    ),
  },
  {
    title: 'Networking',
    text: 'Empresas, talento e oportunidades reais.',
    tone: 'periwinkle',
    icon: (
      <>
        <circle cx="9" cy="8" r="3" />
        <circle cx="17" cy="9" r="2.5" />
        <path d="M3.5 20a5.5 5.5 0 0 1 11 0M14 15.5a4.5 4.5 0 0 1 6.5 4" />
      </>
    ),
  },
  {
    title: 'Convívio',
    text: 'Momentos sociais para tornar a experiência memorável.',
    tone: 'sand',
    // Chávena de café com vapor: o convívio é o intervalo para conversar.
    icon: (
      <>
        <path d="M5 9h11v5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5z" />
        <path d="M16 10.5h1.5a2.5 2.5 0 0 1 0 5H16" />
        <path d="M8 3v3M12 3v3M3.5 21.5h14" />
      </>
    ),
  },
];

export default function ProgramSection() {
  return (
    <section className="section section--surface">
      <div className="container">
        <div className="section-heading">
          <div>
            <p className="eyebrow">&lt;PROGRAMA /&gt;</p>
            <h2>Quatro dias para descobrir.</h2>
          </div>
          <p className="lead">
            Explora quatro dias de tecnologia, aprendizagem, networking e comunidade.
          </p>
        </div>
        <div className="programme-preview">
          {items.map((item) => (
            <article className="programme-preview__item" key={item.title}>
              <div className={`icon icon--${item.tone}`} aria-hidden="true">
                <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
                  {item.icon}
                </svg>
              </div>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
        <div className="actions" style={{ justifyContent: 'center' }}>
          <Link className="btn btn--primary" to="/agenda">
            Ver agenda
          </Link>
        </div>
      </div>
    </section>
  );
}
