import { useEffect, useRef, useState } from 'react';

/**
 * Devolve um ref e um booleano que passa a true (e fica true) quando o elemento
 * entra no ecrã. Usa IntersectionObserver, por isso não pesa no scroll.
 */
export function useInView<T extends Element>(threshold = 0.15, rootMargin = '0px 0px -8% 0px') {
    const ref = useRef<T | null>(null);
    // Sem suporte a IntersectionObserver, mostra tudo logo (sem animação)
    const [inView, setInView] = useState(() => typeof IntersectionObserver === 'undefined');

    useEffect(() => {
        const element = ref.current;
        if (!element || typeof IntersectionObserver === 'undefined') return;

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setInView(true);
                    observer.disconnect(); // anima só na primeira vez
                }
            },
            { threshold, rootMargin },
        );

        observer.observe(element);
        return () => observer.disconnect();
    }, [threshold, rootMargin]);

    return { ref, inView };
}