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
  const items = useMemo(() => {
    const q = normalize(query);
    return FAQ_DATA.filter(
      (item) =>
        (category === 'todos' || item.category === category) &&
        (!q || normalize(`${item.question} ${item.answer}`).includes(q)),
    );
  }, [query, category]);

  return (
    <section className="section">
      <div className="container faq-layout">
        <div className="faq-heading">
          <p className="eyebrow">&lt;FAQ /&gt;</p>
          <h2>Perguntas frequentes</h2>
        </div>
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
        <aside className="faq-nav" aria-label="Categorias de ajuda">
          {CATEGORIES.map((c) => (
            <button key={c.id} type="button" aria-pressed={category === c.id} onClick={() => onCategoryChange(c.id)}>
              {c.label}
            </button>
          ))}
        </aside>
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
              Não encontrámos uma resposta. Experimenta outra pesquisa ou contacta a equipa.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
