import { useMemo } from 'react';
import FaqItem from './FaqItem';
import { CATEGORIES, FAQ_DATA } from './faqData';

type Props = {
  query: string;
  category: string;
  onCategoryChange: (category: string) => void;
};

/** Texto sem acentos e em minúsculas, como a pesquisa do protótipo. */
const normalize = (value: string) =>
  value
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();

/** Perguntas frequentes (`ui-ux/informacao-ajuda`): categorias à esquerda, lista à direita, pesquisa no cabeçalho. */
export default function FaqSection({ query, category, onCategoryChange }: Props) {
  const searching = normalize(query) !== '';
  const items = useMemo(() => {
    const q = normalize(query);
    // Enquanto se pesquisa, procura-se em todas as perguntas, seja qual for a categoria escolhida.
    return FAQ_DATA.filter(
      (item) =>
        (q !== '' || category === 'todos' || item.category === category) &&
        (!q || normalize(`${item.question} ${item.answer}`).includes(q)),
    );
  }, [query, category]);

  return (
    <section className={`section faq-section${searching ? " faq-section--searching" : ""}`}>
      <div className={`container faq-layout${searching ? " faq-layout--searching" : ""}`}>
        <div className="faq-heading">
          <p className="eyebrow">&lt;DÚVIDAS /&gt;</p>
          <h2>{searching ? "Resultados da pesquisa" : "Perguntas frequentes"}</h2>
          {searching && (
            <p className="faq-status" role="status" aria-live="polite">
              {items.length === 0
                ? `Sem resultados para «${query.trim()}».`
                : `${items.length} ${items.length === 1 ? "resultado" : "resultados"} para «${query.trim()}».`}
            </p>
          )}
        </div>
        {!searching && (
        <label className="faq-mobile-filter">
          <span>Categoria</span>
          <select value={category} onChange={(event) => onCategoryChange(event.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        )}
        {!searching && (
        <div className="faq-nav" role="group" aria-label="Categorias de ajuda">
          {CATEGORIES.map((c) => (
            <button key={c.id} type="button" aria-pressed={category === c.id} onClick={() => onCategoryChange(c.id)}>
              {c.label}
            </button>
          ))}
        </div>
        )}
        <div className="faq-list">
          {items.map((item, index) => (
            // A chave inclui a categoria e a pesquisa: o primeiro item abre sempre por omissão, como no protótipo.
            <FaqItem
              key={`${item.id}-${category}-${query}`}
              question={item.question}
              answer={item.answer}
              category={item.category}
              defaultOpen={index === 0 && !query}
            />
          ))}
          {items.length === 0 && (
            <div className="faq-empty">
              Não encontrámos uma resposta. Experimenta outra pesquisa ou escreve-nos para{' '}
              <a href="mailto:geral@eneiconf.pt">geral@eneiconf.pt</a>.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
