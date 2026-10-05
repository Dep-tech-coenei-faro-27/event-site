import { useState, useRef, useEffect } from 'react';

const EMAIL = /([\w.+-]+@[\w-]+\.[\w.]+)/g;

// Transforma emails no texto em links mailto
function withLinks(text: string) {
  return text.split(EMAIL).map((part, i) =>
    i % 2 === 1 ? (
      <a key={i} href={`mailto:${part}`} className="text-[#23caff] underline underline-offset-4 hover:text-white">
        {part}
      </a>
    ) : (
      part
    ),
  );
}

type Props = { question: string; answer: string; defaultOpen?: boolean };

export default function FaqItem({ question, answer, defaultOpen = false }: Props) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.style.maxHeight = isOpen ? `${contentRef.current.scrollHeight}px` : '0px';
    }
  }, [isOpen]);

  return (
    <div
      className={`azulejo-bg overflow-hidden rounded-xl border px-4 transition-colors duration-200 ${
        isOpen ? 'border-[#1ab2ff]/40 bg-[#0a1930]' : 'border-white/10 bg-[#0a172f]'
      }`}
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        className="flex min-h-[58px] w-full cursor-pointer items-center justify-between py-4 text-left text-[15px] font-bold leading-snug text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1ab2ff]"
      >
        <span>{question}</span>
        <svg viewBox="0 0 24 24" aria-hidden="true" className="ml-4 h-5 w-5 shrink-0 fill-none stroke-[#1ab2ff] stroke-2" strokeLinecap="round">
          <path d="M5 12h14" />
          <path d="M12 5v14" className={`origin-center transition-transform duration-300 ${isOpen ? 'scale-y-0' : 'scale-y-100'}`} />
        </svg>
      </button>

      <div
        ref={contentRef}
        style={{ maxHeight: defaultOpen ? undefined : 0 }}
        className="overflow-hidden transition-[max-height] duration-300 ease-in-out"
      >
        <p className="pb-4 pr-8 text-sm text-[#b1bccd]">{withLinks(answer)}</p>
      </div>
    </div>
  );
}