import { useRef, useState } from 'react';
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
  usePageMeta('Informações e ajuda · ENEI 2027', 'Encontra respostas às tuas perguntas sobre o ENEI 2027.');

  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('todos');
  const searching = query.trim() !== '';
  // Os mapas só entram com animação quando voltam depois de uma pesquisa, não ao abrir a página.
  const [hasSearched, setHasSearched] = useState(false);
  const searchInput = useRef<HTMLInputElement>(null);
  if (searching && !hasSearched) setHasSearched(true);

  // «Ver mapa» nos canais de apoio: com uma pesquisa feita os mapas não estão na página, por isso limpa-se a pesquisa
  // e desce-se até eles quando voltarem.
  const showMap = () => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const go = () => document.getElementById('localizacoes')?.scrollIntoView({ block: 'start', behavior: reduced ? 'auto' : 'smooth' });
    if (query.trim() === '') {
      go();
    } else {
      setQuery('');
      window.setTimeout(go, 60);
    }
  };

  return (
    <>
      <header className="page-hero center">
        <div className="container">
          <p className="eyebrow">&lt;AJUDA /&gt;</p>
          <h1>Como podemos ajudar?</h1>
          <p className="lead">Encontra respostas às tuas perguntas sobre o ENEI 2027.</p>
          <div className="search">
            <input
              ref={searchInput}
              type="search"
              aria-label="Pesquisar perguntas"
              placeholder="Pesquisa uma pergunta…"
              autoComplete="off"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            {query !== '' && (
              <button
                type="button"
                className="search__clear"
                aria-label="Limpar pesquisa"
                onClick={() => {
                  setQuery('');
                  searchInput.current?.focus();
                }}
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </header>
      {/* Enquanto se pesquisa, os mapas e a contagem saem e os resultados aparecem logo por baixo da barra. */}
      {!searching && <LocationSection animateIn={hasSearched} />}
      <FaqSection query={query} category={category} onCategoryChange={setCategory} />
      <ContactSection onShowMap={showMap} />
    </>
  );
}
