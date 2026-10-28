import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

/** Os separadores da área pessoal (a moldura mantém-se montada entre eles). */
const ACCOUNT_TABS = ['/perfil', '/conta/dados', '/conta/seguranca'];

/**
 * Cada mudança de rota volta ao topo; com `#âncora` desce à secção.
 * O salto à âncora volta a ser feito enquanto a página ainda muda de tamanho (imagens, fontes e animações de entrada
 * empurram a secção depois do primeiro scroll) e pára logo que a pessoa mexe no scroll ou passa 1,5 s.
 */
export default function ScrollToTop() {
  const { pathname, hash } = useLocation();
  const previousPath = useRef<string | null>(null);

  useEffect(() => {
    const previous = previousPath.current;
    previousPath.current = pathname;

    if (!hash) {
      // Mudar de separador na área pessoal só troca o conteúdo: a página fica onde estava.
      if (previous !== null && previous !== pathname && ACCOUNT_TABS.includes(previous) && ACCOUNT_TABS.includes(pathname)) return;
      window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
      return;
    }

    const id = decodeURIComponent(hash.slice(1));
    const go = () => document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: 'instant' });
    go();

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
