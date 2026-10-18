import { act, cleanup, render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { revealProgress, useMotion } from "./useMotion";

function Layer() {
  useMotion();
  return null;
}

function Page() {
  return (
    <>
      <header className="site-header" />
      <main>
        <section className="hero-home" />
        <section className="section home-edition">
          <div className="container split">
            <div>a</div>
            <div>b</div>
          </div>
        </section>
        <section className="section">
          <div className="photo home-faro-photo">
            <img alt="" />
          </div>
          <article className="pathway">p1</article>
          <article className="pathway">p2</article>
          <article className="pathway">p3</article>
        </section>
      </main>
    </>
  );
}

const VH = 1000;

function stubEnvironment(reduced: boolean) {
  vi.stubGlobal("matchMedia", () => ({ matches: reduced, addEventListener() {}, removeEventListener() {} }));
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    cb(0);
    return 1;
  });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: VH });
  Object.defineProperty(document.documentElement, "scrollHeight", { configurable: true, value: 4000 });
  Object.defineProperty(window, "scrollY", { configurable: true, writable: true, value: 0 });
}

function mount() {
  return render(
    <MemoryRouter>
      <Layer />
      <Page />
    </MemoryRouter>,
  );
}

/** Põe o elemento a `top` px do topo do ecrã (no scroll atual) e com `height` de altura, pelo layout. */
function place(el: Element, top: number, height = 200) {
  Object.defineProperty(el, "offsetTop", { configurable: true, value: top + window.scrollY });
  Object.defineProperty(el, "offsetHeight", { configurable: true, value: height });
}
const scroll = () => act(() => void window.dispatchEvent(new Event("scroll")));
const reveal = (el: Element | null) => Number((el as HTMLElement).style.getPropertyValue("--reveal"));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  document.body.removeAttribute("style");
});

describe("revealProgress", () => {
  it("0 enquanto o elemento está por baixo do ecrã e 1 quando já subiu o suficiente", () => {
    expect(revealProgress(1500, 200, VH)).toBe(0);
    expect(revealProgress(VH, 200, VH)).toBe(0); // acabou de tocar no fundo
    expect(revealProgress(VH - 300, 200, VH)).toBe(1); // subiu mais do que os 220px (22% do ecrã) que precisa
    expect(revealProgress(-300, 200, VH)).toBe(1); // já passou por cima
  });

  it("cresce de forma contínua com o scroll e volta atrás ao subir", () => {
    const values = [1000, 950, 900, 850, 800].map((top) => revealProgress(top, 200, VH));
    for (let i = 1; i < values.length; i++) expect(values[i]).toBeGreaterThan(values[i - 1]);
    expect(values[0]).toBe(0);
  });

  it("é «ease-out»: a meio do trajeto já vai a mais de metade (aparece depressa e assenta devagar)", () => {
    const half = revealProgress(VH - 110, 200, VH); // 110 de 220px
    expect(half).toBeCloseTo(0.75, 3);
  });

  it("um título pequeno tem um trajeto que se nota (pelo menos 22% do ecrã), não 80px", () => {
    expect(revealProgress(VH - 80, 100, VH)).toBeLessThan(0.7);
    expect(revealProgress(VH - 220, 100, VH)).toBe(1);
  });

  it("um elemento grande não precisa de subir mais de 40% do ecrã", () => {
    expect(revealProgress(VH - 400, 900, VH)).toBe(1);
    expect(revealProgress(VH - 200, 900, VH)).toBeCloseTo(0.75, 3);
  });

  it("nunca precisa de mais scroll do que o que ainda existe: no fim da página chega a 1", () => {
    // só restam 60px de scroll depois de o elemento entrar: sem este limite ficava a ~27%
    expect(revealProgress(VH - 60, 100, VH, 0, 60)).toBe(1);
    expect(revealProgress(VH - 60, 100, VH, 0)).toBeLessThan(0.5);
  });

  it("o atraso adia o início sem impedir que acabe no mesmo sítio", () => {
    expect(revealProgress(900, 200, VH, 0.28)).toBeLessThan(revealProgress(900, 200, VH, 0));
    expect(revealProgress(VH - 300, 200, VH, 0.28)).toBe(1);
  });
});

describe("useMotion", () => {
  beforeEach(() => stubEnvironment(false));

  it("marca o body, desenha a barra de progresso e tira tudo ao desmontar", () => {
    const { unmount } = mount();
    expect(document.body).toHaveClass("motion-ready");
    expect(document.querySelector(".site-progress__bar")).not.toBeNull();
    unmount();
    expect(document.body).not.toHaveClass("motion-ready");
    expect(document.querySelector(".site-progress")).toBeNull();
  });

  it("marca os elementos que se revelam (com a direção certa) e as molduras das imagens", () => {
    mount();
    expect(document.querySelector<HTMLElement>(".pathway")!.dataset.motionItem).toBe("up");
    expect(document.querySelector<HTMLElement>(".home-faro-photo")!.dataset.motionItem).toBe("left");
    expect(document.querySelector(".home-faro-photo")).toHaveClass("motion-media");
    expect(document.querySelectorAll("main > .section.motion-section")).toHaveLength(2);
    expect(document.querySelectorAll(".motion-section__trace")).toHaveLength(2);
  });

  it("DESCER revela e SUBIR desfaz: o elemento acompanha o scroll nos dois sentidos", () => {
    mount();
    const pathway = document.querySelector(".pathway")!;

    place(pathway, 1400); // por baixo do ecrã
    scroll();
    expect(reveal(pathway)).toBe(0);

    place(pathway, 920); // entrou um pouco
    scroll();
    const entering = reveal(pathway);
    expect(entering).toBeGreaterThan(0);
    expect(entering).toBeLessThan(1);

    place(pathway, 700); // já bem dentro
    scroll();
    expect(reveal(pathway)).toBe(1);

    place(pathway, 920); // voltou a subir (o scroll foi para cima): desvanece outra vez
    scroll();
    expect(reveal(pathway)).toBeCloseTo(entering, 3);

    place(pathway, 1400);
    scroll();
    expect(reveal(pathway)).toBe(0);
  });

  it("os elementos de uma fila entram em cascata (o seguinte começa um pouco depois)", () => {
    mount();
    const [a, b, c] = document.querySelectorAll(".pathway");
    [a, b, c].forEach((el) => place(el, 920));
    scroll();
    expect(reveal(a)).toBeGreaterThan(reveal(b));
    expect(reveal(b)).toBeGreaterThan(reveal(c));
  });

  it("a imagem de Faro (e a sua moldura) acompanha o scroll", () => {
    mount();
    const photo = document.querySelector(".home-faro-photo")!;
    place(photo, 1200, 480);
    scroll();
    expect(reveal(photo)).toBe(0);
    place(photo, 560, 480); // subiu 440px, mais do que os 400px (40% do ecrã) que precisa
    scroll();
    expect(reveal(photo)).toBe(1);
  });

  it("o traço de cada secção cresce com a secção a entrar e encolhe ao sair", () => {
    mount();
    const section = document.querySelectorAll("main > .section")[0];
    const trace = section.querySelector(".motion-section__trace")!;
    place(section, 1300, 800);
    scroll();
    expect(reveal(trace)).toBe(0);
    place(section, 850, 800);
    scroll();
    expect(reveal(trace)).toBeGreaterThan(0);
    expect(reveal(trace)).toBeLessThan(1);
    place(section, 500, 800);
    scroll();
    expect(reveal(trace)).toBe(1);
    place(section, 1300, 800);
    scroll();
    expect(reveal(trace)).toBe(0);
  });

  it("não escreve no DOM se o valor não mudou (scroll não deve gerar trabalho à toa)", () => {
    mount();
    const pathway = document.querySelector<HTMLElement>(".pathway")!;
    place(pathway, 1400);
    scroll();
    const spy = vi.spyOn(pathway.style, "setProperty");
    scroll();
    scroll();
    expect(spy).not.toHaveBeenCalled();
  });

  it("ao fazer scroll atualiza o progresso e o cabeçalho", () => {
    mount();
    expect(document.body.style.getPropertyValue("--scroll-progress")).toBe("0");
    Object.defineProperty(window, "scrollY", { configurable: true, writable: true, value: 1500 });
    scroll();
    expect(document.body.style.getPropertyValue("--scroll-progress")).toBe("0.5");
    expect(document.querySelector(".site-header")).toHaveClass("motion-header--scrolled");
    Object.defineProperty(window, "scrollY", { configurable: true, writable: true, value: 0 });
    scroll();
    expect(document.querySelector(".site-header")).not.toHaveClass("motion-header--scrolled");
  });

  it("ao sair da página tira os traços e deixa de ouvir o scroll", () => {
    const { unmount } = mount();
    const pathway = document.querySelector(".pathway")!;
    unmount();
    expect(document.querySelectorAll(".motion-section__trace")).toHaveLength(0);
    place(pathway, 1400);
    scroll();
    expect(reveal(pathway)).not.toBe(0);
  });
});

describe("useMotion com prefers-reduced-motion", () => {
  it("mostra tudo logo (--reveal a 1), sem depender do scroll", () => {
    stubEnvironment(true);
    mount();
    document.querySelectorAll("[data-motion-item], .motion-section__trace").forEach((el) => expect(reveal(el)).toBe(1));
    const pathway = document.querySelector(".pathway")!;
    place(pathway, 1400);
    scroll();
    expect(reveal(pathway)).toBe(1);
  });
});
