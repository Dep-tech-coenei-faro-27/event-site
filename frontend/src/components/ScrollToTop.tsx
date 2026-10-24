import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { MAIN_ID } from './SkipLink';

/**
 * Numa SPA o browser não anuncia a mudança de página: o foco ficava no link carregado (ou caía no <body>) e o leitor
 * de ecrã não dizia nada. Ao mudar de rota, o foco passa para o <h1> da nova página, que o leitor de ecrã lê.
 * Páginas que ainda estão a carregar só mostram o <h1> depois; espera-se até 1 s e, sem <h1>, foca-se o <main>.
 * Numa ligação para uma secção (`#âncora`), o foco vai para essa secção.
 */
function focus(el: HTMLElement) {
  if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
  el.focus({ preventScroll: true });
}

function focusPageHeading(): () => void {
  const main = document.getElementById(MAIN_ID);
  if (!main) return () => {};

  const h1 = main.querySelector<HTMLElement>('h1');
  if (h1) {
    focus(h1);
    return () => {};
  }

  const observer = new MutationObserver(() => {
    const found = main.querySelector<HTMLElement>('h1');
    if (found) {
      done();
      focus(found);
    }
  });
  const timer = window.setTimeout(() => {
    done();
    focus(main);
  }, 1000);
  const done = () => {
    observer.disconnect();
    window.clearTimeout(timer);
  };
  observer.observe(main, { childList: true, subtree: true });
  return done;
}

/**
 * Cada mudança de rota volta ao topo; com `#âncora` desce à secção.
 * O salto à âncora volta a ser feito enquanto a página ainda muda de tamanho (imagens, fontes e animações de entrada
 * empurram a secção depois do primeiro scroll) e pára logo que a pessoa mexe no scroll ou passa 1,5 s.
 */
export default function ScrollToTop() {
  const { pathname, hash } = useLocation();
  const isFirstRender = useRef(true);

  useEffect(() => {
    // No primeiro carregamento o leitor de ecrã já anuncia a página; só se move o foco nas mudanças seguintes.
    const firstRender = isFirstRender.current;
    isFirstRender.current = false;

    if (!hash) {
      window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
      return firstRender ? undefined : focusPageHeading();
    }

    const id = decodeURIComponent(hash.slice(1));
    const go = () => document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: 'instant' });
    go();
    // Ligação para uma secção (`#contacto`): o foco vai para a secção, para o leitor de ecrã continuar a partir dela.
    const target = document.getElementById(id);
    if (!firstRender && target) focus(target);

    const stop = () => {
      observer.disconnect();
      window.clearTimeout(timer);
      window.removeEventListener('wheel', stop);
      window.removeEventListener('touchstart', stop);
      window.removeEventListener('keydown', stop);
    };
    const observer = new ResizeObserver(go);
    observer.observe(document.body);
    const timer = window.setTimeout(stop, 1500);
    window.addEventListener('wheel', stop, { passive: true });
    window.addEventListener('touchstart', stop, { passive: true });
    window.addEventListener('keydown', stop);
    return stop;
  }, [pathname, hash]);

  return null;
}
