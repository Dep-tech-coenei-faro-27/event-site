import { useEffect, useId, useRef, useState } from 'react';

const EMAIL = /([\w.+-]+@[\w-]+\.[\w.]+)/g;

// Transforma emails no texto em links mailto
function withLinks(text: string) {
  return text.split(EMAIL).map((part, i) =>
    i % 2 === 1 ? (
      <a key={i} href={`mailto:${part}`}>
        {part}
      </a>
    ) : (
      part
    ),
  );
}

type Props = { question: string; answer: string; category: string; defaultOpen?: boolean };

/**
 * Pergunta do FAQ (`ui-ux/informacao-ajuda`): botão com `aria-expanded` e resposta em região, que abre e fecha
 * com a mesma animação do protótipo (altura e opacidade, 220 ms a abrir e 180 ms a fechar; sem animação com
 * `prefers-reduced-motion`).
 */
export default function FaqItem({ question, answer, category, defaultOpen = false }: Props) {
  const id = useId();
  const [open, setOpen] = useState(defaultOpen);
  // `hidden` só passa a true depois de a animação de fecho acabar.
  const [hidden, setHidden] = useState(!defaultOpen);
  const answerRef = useRef<HTMLDivElement>(null);
  const pending = useRef<'open' | 'close' | null>(null);

  const canAnimate = () =>
    typeof answerRef.current?.animate === 'function' &&
    !(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      setHidden(false);
      pending.current = canAnimate() ? 'open' : null;
    } else if (canAnimate()) {
      pending.current = 'close';
    } else {
      setHidden(true);
    }
  };

  // Só anima (a mudança de estado fez-se no clique): a resposta abre e fecha em altura e opacidade, como no protótipo.
  useEffect(() => {
    const mode = pending.current;
    pending.current = null;
    const element = answerRef.current;
    if (!mode || !element) return;
    element.getAnimations().forEach((animation) => animation.cancel());
    const height = element.scrollHeight;
    if (mode === 'open') {
      element.animate(
        [
          { height: '0px', opacity: 0 },
          { height: `${height}px`, opacity: 1 },
        ],
        { duration: 220, easing: 'cubic-bezier(0, 0, 0.2, 1)' },
      );
      return;
    }
    element
      .animate(
        [
          { height: `${height}px`, opacity: 1 },
          { height: '0px', opacity: 0 },
        ],
        { duration: 180, easing: 'cubic-bezier(0.4, 0, 1, 1)' },
      )
      .finished.then(() => setHidden(true))
      .catch(() => undefined);
  }, [open]);

  return (
    <article className="faq-item" data-category={category}>
      <button
        type="button"
        id={`${id}-question`}
        className="faq-question"
        aria-expanded={open}
        aria-controls={`${id}-answer`}
        onClick={toggle}
      >
        {question}
      </button>
      <div
        id={`${id}-answer`}
        ref={answerRef}
        className="faq-answer"
        role="region"
        aria-labelledby={`${id}-question`}
        hidden={hidden}
      >
        {withLinks(answer)}
      </div>
    </article>
  );
}
