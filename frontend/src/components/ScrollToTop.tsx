import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Cada mudança de rota volta ao topo; com `#âncora` desce à secção.
 * O salto à âncora volta a ser feito enquanto a página ainda muda de tamanho (imagens, fontes e animações de entrada
 * empurram a secção depois do primeiro scroll) e pára logo que a pessoa mexe no scroll ou passa 1,5 s.
 */
export default function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (!hash) {
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
