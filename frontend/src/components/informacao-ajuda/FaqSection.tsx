import { useMemo, useState } from 'react';
import FaqItem from './FaqItem';
import { CATEGORIES, FAQ_DATA } from './faqData';
import Eyebrow from '../EyeBrow';

type Props = { query: string };

export default function FaqSection({ query }: Props) {
  const [category, setCategory] = useState<string>('todos');

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    return FAQ_DATA.filter(
      (i) =>
        (category === 'todos' || i.category === category) &&
        (!q || `${i.question} ${i.answer}`.toLowerCase().includes(q)),
    );
  }, [query, category]);

  return (
    <section className="bg-[#050d21] py-[clamp(72px,9vw,124px)]">
      <div className="mx-auto w-[min(calc(100%-28px),1180px)] sm:w-[min(calc(100%-40px),1180px)]">
        <Eyebrow text='FAQ'/>
        <h2 className="text-[clamp(30px,4vw,52px)] font-semibold leading-[1.06] tracking-[-0.045em] text-white">
          Perguntas frequentes
        </h2>

        {/* Mobile: select */}
        <label className="mt-6 grid gap-2 sm:hidden">
          <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#8796a9]">Categoria</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-12 w-full rounded-lg border border-[#1ab2ff]/40 bg-[#0a172f] px-4 text-[13px] font-semibold text-white outline-none focus:border-[#1ab2ff]"
          >
            {CATEGORIES.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
        </label>

        {/* Desktop: botões */}
        <div
          role="group"
          aria-label="Categorias de ajuda"
          className="mt-6 hidden grid-cols-3 gap-1 rounded-xl border border-white/10 bg-[#0a172f] p-2 sm:grid lg:grid-cols-6"
        >
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              type="button"
              aria-pressed={category === c.id}
              onClick={() => setCategory(c.id)}
              className={`min-h-[42px] cursor-pointer rounded-[7px] border px-2.5 py-2 text-xs transition-colors ${
                category === c.id
                  ? 'border-[#1ab2ff]/50 bg-[#1ab2ff]/15 text-white'
                  : 'border-transparent text-[#b1bccd] hover:text-white'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="mt-6 space-y-2">
          {items.map((item, idx) => (
            // key inclui a categoria/pesquisa para o primeiro item abrir sempre por defeito
            <FaqItem
              key={`${item.id}-${category}-${query}`}
              question={item.question}
              answer={item.answer}
              defaultOpen={idx === 0 && !query}
            />
          ))}
          {items.length === 0 && (
            <div className="rounded-2xl border border-dashed border-[#1ab2ff]/40 p-8 text-center text-[#b1bccd]">
              Não encontrámos uma resposta. Experimenta outra pesquisa ou contacta a equipa.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}