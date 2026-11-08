import { useLayoutEffect } from "react";

/**
 * Marca o `<body>` com `data-page`, que é o que o CSS das páginas no desenho novo usa para se
 * limitar a essa página (ver `home.css`, `checkout.css`). Sai ao desmontar, para a página seguinte
 * começar limpa. `bodyClass` acrescenta uma classe ao `<body>` (o protótipo põe aí, por exemplo,
 * `payment-result-page`) e também sai ao desmontar.
 */
export function useBodyPage(page: string, bodyClass?: string) {
  useLayoutEffect(() => {
    document.body.dataset.page = page;
    const classes = bodyClass ? bodyClass.split(" ") : [];
    document.body.classList.add(...classes);
    return () => {
      delete document.body.dataset.page;
      document.body.classList.remove(...classes);
    };
  }, [page, bodyClass]);
}
