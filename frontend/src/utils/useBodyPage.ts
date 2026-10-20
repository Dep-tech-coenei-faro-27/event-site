import { useEffect } from "react";

/**
 * Marca o `<body>` com `data-page`, que é o que o CSS das páginas no desenho novo usa para se
 * limitar a essa página (ver `home.css`). Sai ao desmontar, para a página seguinte começar limpa.
 */
export function useBodyPage(page: string) {
  useEffect(() => {
    document.body.dataset.page = page;
    return () => {
      delete document.body.dataset.page;
    };
  }, [page]);
}
