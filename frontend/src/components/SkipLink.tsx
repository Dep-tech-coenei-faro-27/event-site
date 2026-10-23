import type { MouseEvent } from 'react';

/** O `id` do `<main>` da aplicação (App.tsx), para onde a ligação leva. */
export const MAIN_ID = 'conteudo';

/**
 * «Saltar para o conteúdo»: o primeiro elemento focável de cada página. Fica fora do ecrã até
 * receber foco (não usa `hidden`, que a tiraria da ordem de tabulação). Ao ativar, move o foco
 * para o `<main>` sem mudar o endereço: um `#conteudo` no URL faria o router tratá-lo como âncora.
 */
export default function SkipLink() {
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    const main = document.getElementById(MAIN_ID);
    if (!main) return;
    event.preventDefault();
    main.focus();
    main.scrollIntoView?.({ block: 'start' });
  };

  return (
    <a
      href={`#${MAIN_ID}`}
      onClick={onClick}
      className="fixed left-4 -top-20 focus:top-4 z-[1000] rounded-lg bg-acento-principal px-4 py-2.5 font-poppins text-sm font-extrabold text-azul-base no-underline transition-[top] duration-150 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-branco"
    >
      Saltar para o conteúdo
    </a>
  );
}
