import { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";

// Camada de animações do desenho novo: porta do `ui-ux/motion.js` para o React, com uma diferença
// de propósito: as revelações NÃO acontecem uma só vez, **acompanham a posição do scroll**. Cada
// elemento que aparece (`data-motion-item`), cada imagem que se revela e o traço de cada secção
// recebe uma variável `--reveal` de 0 a 1 que depende de onde está no ecrã; o CSS (`motion.css`,
// `home.css`) liga a opacidade, o deslocamento e o corte a essa variável. Descer faz aparecer,
// voltar a subir desfaz, e parar a meio deixa a meio.
//
// Também marca o `<body>` como `motion-ready`, desenha a barra de progresso do scroll e atualiza as
// variáveis do cabeçalho e do deslocamento do hero.
//
// Não se porta o desvanecer ao clicar numa ligação do `motion.js`: aquilo era para páginas HTML
// separadas; aqui o router já troca de página sem recarregar.

type Direction = "up" | "left" | "right";

const REVEAL_GROUPS: [string, Direction][] = [
  [".section-heading > *", "up"],
  [".home-edition .split > *", "up"],
  [".pathway", "up"],
  [".programme-preview__item", "up"],
  [".home-programme__item", "up"],
  [".home-practical .split > *", "up"],
  [".home-faro-photo", "left"],
  [".home-experience .split > *", "up"],
  // Estes dois não vêm do protótipo: no React a «Experiência» e o texto de Faro têm outra estrutura e
  // ficavam sem animação. As cartas da «Experiência» entram em cascata, uma a uma.
  [".home-experience .container > :not(.ops-strip)", "up"],
  [".ops-item", "up"],
  [".home-faro .split > *", "up"],
  [".home-closing .container > *", "up"],
  [".fact", "up"],
  [".timeline-item", "up"],
  [".photo", "up"],
  [".speaker-profile", "up"],
  [".experience-tile", "up"],
  [".team-department__header", "left"],
  [".team-member", "up"],
  [".benefit-item", "up"],
  [".tier", "up"],
  [".logo-placeholder", "up"],
  [".ticket-card", "up"],
  [".checkout-step", "up"],
  [".checkout-panel", "left"],
  [".auth-intro > *", "left"],
  [".auth-card", "right"],
  [".account-content > *", "up"],
  [".location-card", "up"],
  [".countdown", "up"],
  [".faq-layout > *", "up"],
  [".legal-layout > *", "up"],
  [".system-state-content > *", "up"],
  [".payment-status > *", "up"],
  [".checkout-heading__copy > *", "up"],
  [".registration-checklist > *", "up"],
  [".programme-axis", "up"],
  [".platform-flow__item", "up"],
  [".support-panel", "right"],
  [".legal-section", "up"],
  [".footer-main > *", "up"],
];

// Restantes páginas (Sobre, Agenda, Equipa, Informação e Ajuda, Bilhetes, legais, conta...).
// O React já as tinha em Tailwind, sem as classes do protótipo, por isso a camada de animações apanha-as
// pela estrutura e **não é preciso mexer nos ficheiros das páginas**: cada secção tem um contentor com
// um bloco de título e depois o conteúdo. O bloco de título e cada item de uma grelha ou de uma lista
// entram com o scroll, como na página inicial. Uma grelha não se anima a ela própria (os itens é que
// entram, em cascata), para o mesmo conteúdo não desvanecer duas vezes.
// Fora ficam os elementos decorativos (`aria-hidden`, `pointer-events-none`): a revelação mexia-lhes na
// opacidade e a marca de água do símbolo, a 7 %, passava a 100 %.
const CONTENT = ":not([aria-hidden='true']):not(.pointer-events-none):not(script)";
const PAGE_GROUPS: [string, Direction][] = [
  [`main section > div > :not(.grid):not([class*='grid-cols']):not(.flex-col):not(aside)${CONTENT}`, "up"],
  [`main section > div > .grid > *${CONTENT}`, "up"],
  [`main section > div > [class*='grid-cols'] > *${CONTENT}`, "up"],
  [`main section > div > .flex-col > *${CONTENT}`, "up"],
];

const MEDIA_SELECTOR =
  ".photo, .campus-photo, .location-card__visual, .home-faro-photo, .team-member__photo, .speaker-profile__media";

const HERO_SELECTOR = ".hero-home, .hero";

/** Fração do atraso entre elementos seguidos (0 a 0.28), para entrarem em cascata. */
const STAGGER = 0.07;
const MAX_STAGGER = 0.28;

/**
 * Progresso (0 a 1) da revelação de um elemento, segundo a sua posição no ecrã.
 * - 0 enquanto o topo está por baixo do ecrã; começa a subir quando o topo entra pelo fundo;
 * - chega a 1 depois de o elemento ter subido uma distância (a sua altura, entre 22% e 40% do ecrã:
 *   um título pequeno também tem um trajeto que se nota);
 * - nunca precisa de mais scroll do que o que ainda existe (`travel`): um elemento no fim da página
 *   chega a 1 quando a página acaba, em vez de ficar a meio para sempre;
 * - a curva é «ease-out»: desvanece depressa ao entrar e assenta devagar;
 * - `delay` (0 a 1) atrasa o início, para os elementos de uma fila entrarem em cascata.
 */
export function revealProgress(
  top: number,
  height: number,
  viewportHeight: number,
  delay = 0,
  travel = Infinity,
): number {
  const wanted = Math.min(Math.max(height, viewportHeight * 0.22), viewportHeight * 0.4);
  const range = Math.max(8, Math.min(wanted, travel));
  const raw = (viewportHeight - top) / range;
  const linear = Math.max(0, Math.min(1, (raw - delay) / (1 - delay)));
  return 1 - (1 - linear) * (1 - linear);
}

/**
 * Posição do elemento desde o topo do documento, pelo layout (`offsetTop`), que NÃO muda com o
 * deslocamento da própria animação. Medir com `getBoundingClientRect` faria o elemento mover-se
 * quando se revela e isso mudava a medição: o resultado dependia do sentido do scroll.
 */
function documentTop(element: HTMLElement): number {
  let y = 0;
  let node: HTMLElement | null = element;
  while (node) {
    y += node.offsetTop;
    node = node.offsetParent as HTMLElement | null;
  }
  return y;
}

type Tracked = {
  /** Onde se escreve `--reveal`. */
  target: HTMLElement;
  /** De onde se mede a posição (a própria, ou a da secção no caso do traço). */
  source: HTMLElement;
  delay: number;
  last: number;
};

export function useMotion() {
  const { pathname } = useLocation();

  // Uma vez: a marca no body e a barra de progresso.
  useLayoutEffect(() => {
    document.body.classList.add("motion-ready");
    const progress = document.createElement("div");
    progress.className = "site-progress";
    progress.setAttribute("aria-hidden", "true");
    progress.innerHTML = '<span class="site-progress__bar"></span>';
    document.body.prepend(progress);
    return () => {
      progress.remove();
      document.body.classList.remove("motion-ready");
    };
  }, []);

  // A cada página: o que se revela com o scroll e as variáveis do scroll.
  useLayoutEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const body = document.body;
    const header = document.querySelector<HTMLElement>(".site-header");
    const hero = document.querySelector<HTMLElement>(HERO_SELECTOR);

    const tracked: Tracked[] = [];
    const seen = new Set<HTMLElement>();
    // As páginas feitas com as classes do protótipo (a inicial e as que já passaram ao desenho novo) usam só os
    // grupos do protótipo; as outras (em Tailwind) usam também a estrutura.
    const fromPrototype = pathname === "/" || document.querySelector("main .page-hero, main > .section") !== null;
    const groups = fromPrototype ? REVEAL_GROUPS : [...REVEAL_GROUPS, ...PAGE_GROUPS];
    groups.forEach(([selector, direction]) => {
      document.querySelectorAll<HTMLElement>(selector).forEach((element, index) => {
        if (seen.has(element)) return;
        seen.add(element);
        element.dataset.motionItem = direction;
        tracked.push({
          target: element,
          source: element,
          delay: Math.min(index * STAGGER, MAX_STAGGER),
          last: -1,
        });
      });
    });

    // Imagens que se revelam: quando a moldura não é um dos elementos acima, também precisa da variável.
    document.querySelectorAll<HTMLElement>(MEDIA_SELECTOR).forEach((element) => {
      element.classList.add("motion-media");
      if (seen.has(element)) return;
      seen.add(element);
      tracked.push({ target: element, source: element, delay: 0, last: -1 });
    });

    // O traço no topo de cada secção cresce com a secção a entrar.
    const traces: HTMLElement[] = [];
    // Na página inicial são as `.section` do protótipo; nas restantes, as secções do topo da página (o
    // React não tem a classe `.section`): as que não estão dentro de outra secção, cabeçalho ou cartão.
    const sections = fromPrototype
        ? document.querySelectorAll<HTMLElement>("main > .section, main > .ag-programme, main > .ag-closing")
        : [...document.querySelectorAll<HTMLElement>("main section")].filter(
            (section) => !section.parentElement?.closest("section, header, article"),
          );
    sections.forEach((section) => {
      section.classList.add("motion-section");
      const trace = document.createElement("span");
      trace.className = "motion-section__trace";
      trace.setAttribute("aria-hidden", "true");
      section.prepend(trace);
      traces.push(trace);
      tracked.push({ target: trace, source: section, delay: 0, last: -1 });
    });

    const setReveal = (item: Tracked, value: number) => {
      const rounded = Math.round(value * 1000) / 1000;
      if (rounded === item.last) return;
      item.last = rounded;
      item.target.style.setProperty("--reveal", String(rounded));
      // As molduras de imagem só levam o corte (e perdem a sombra) enquanto se revelam.
      if (item.target.classList.contains("motion-media")) item.target.toggleAttribute("data-revealed", rounded >= 1);
    };

    let ticking = false;
    let frame = 0;
    const updateScrollState = () => {
      const vh = window.innerHeight;
      const scrollRange = document.documentElement.scrollHeight - vh;
      const progress = scrollRange > 0 ? window.scrollY / scrollRange : 0;
      body.style.setProperty("--scroll-progress", String(Math.max(0, Math.min(1, progress))));
      header?.classList.toggle("motion-header--scrolled", window.scrollY > 20);
      if (hero && !reduced.matches && hero.getBoundingClientRect().bottom > 0) {
        hero.style.setProperty("--hero-shift", `${Math.min(window.scrollY * 0.045, 22)}px`);
      }
      // Primeiro lê as posições todas, depois escreve (evita recalcular o layout a cada elemento).
      const geometry = tracked.map((item) => ({
        top: documentTop(item.source),
        height: item.source.offsetHeight,
      }));
      tracked.forEach((item, index) => {
        const { top: documentY, height } = geometry[index];
        // Scroll que ainda falta depois de o elemento entrar pelo fundo do ecrã.
        const travel = scrollRange - (documentY - vh);
        const top = documentY - window.scrollY;
        setReveal(item, reduced.matches ? 1 : revealProgress(top, height, vh, item.delay, travel));
      });
      ticking = false;
    };
    const requestScrollUpdate = () => {
      if (ticking) return;
      ticking = true;
      frame = requestAnimationFrame(updateScrollState);
    };

    updateScrollState();
    window.addEventListener("scroll", requestScrollUpdate, { passive: true });
    window.addEventListener("resize", requestScrollUpdate);
    window.addEventListener("load", requestScrollUpdate);
    // As imagens e as fontes mudam a altura da página depois de carregar: recalcula quando isso acontece.
    const resizeObserver = typeof ResizeObserver !== "undefined" ? new ResizeObserver(requestScrollUpdate) : undefined;
    resizeObserver?.observe(document.body);

    return () => {
      window.removeEventListener("scroll", requestScrollUpdate);
      window.removeEventListener("resize", requestScrollUpdate);
      window.removeEventListener("load", requestScrollUpdate);
      resizeObserver?.disconnect();
      cancelAnimationFrame(frame);
      traces.forEach((trace) => trace.remove());
      header?.classList.remove("motion-header--scrolled");
    };
  }, [pathname]);
}
