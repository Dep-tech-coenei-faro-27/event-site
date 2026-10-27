import '@testing-library/jest-dom/vitest'

// O jsdom não implementa `scrollIntoView`; o `ScrollToTop` chama-o nas rotas com `#âncora`.
if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = () => {}

// Idem para `ResizeObserver` (o `ScrollToTop` também o usa com `#âncora`).
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}
