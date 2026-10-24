import { useState } from 'react';
import '../informacao-ajuda.css';
import '../informacao-ajuda.overrides.css';
import ContactSection from '../components/informacao-ajuda/ContactSection';
import FaqSection from '../components/informacao-ajuda/FaqSection';
import LocationSection from '../components/informacao-ajuda/MapSection';
import { useBodyPage } from '../utils/useBodyPage';
import { usePageMeta } from '../utils/usePageMeta';

/** `ui-ux/informacao-ajuda`: pesquisa, localizações, FAQ e contacto. O CSS é gerado do protótipo (`informacao-ajuda.css`). */
export default function InformacaoAjudaPage() {
  useBodyPage('informacao-ajuda');
  usePageMeta('Informação · ENEI 2027', 'Encontra respostas às tuas perguntas sobre o ENEI 2027.');

  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('todos');

  return (
    <>
      <header className="page-hero center">
        <div className="container">
          <p className="eyebrow">&lt;AJUDA /&gt;</p>
          <h1>Como podemos ajudar?</h1>
          <p className="lead">Encontra respostas às tuas perguntas sobre o ENEI 2027.</p>
          <label className="search">
            <span className="sr-only">Pesquisar perguntas</span>
            <input
              type="search"
              placeholder="Pesquisa uma pergunta…"
              autoComplete="off"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
      </header>
      <LocationSection />
      <FaqSection query={query} category={category} onCategoryChange={setCategory} />
      <ContactSection />
    </>
  );
}
