import { useLayoutEffect, useRef } from "react";

type Loading = { state: "loading"; message?: string; className?: string };
type Failure = {
  state: "error";
  /** O que falhou e o que fazer (ver `loadErrorMessage`). */
  message: string;
  onRetry: () => void;
  title?: string;
  /** 1 quando o estado ocupa a página inteira (não há outro <h1>); 2 dentro de uma página. */
  titleLevel?: 1 | 2;
  className?: string;
};

/**
 * Estado de um pedido à API: «A carregar…» (`role="status"`) ou a falha com «Tentar novamente»
 * (`role="alert"`). O erro recebe o foco, para o leitor de ecrã e o teclado irem direto ao botão.
 * As cores são da paleta com contraste ≥ 4,5:1 sobre os fundos escuros (docs/frontend-contraste.md).
 */
export default function PageStatus(props: Loading | Failure) {
  const errorRef = useRef<HTMLDivElement>(null);
  const isError = props.state === "error";

  // Antes de pintar: o foco já está no erro quando ele aparece.
  useLayoutEffect(() => {
    if (isError) errorRef.current?.focus();
  }, [isError]);

  if (props.state === "loading") {
    return (
      <div role="status" className={`text-[14px] text-nevoa-azul ${props.className ?? ""}`}>
        {props.message ?? "A carregar…"}
      </div>
    );
  }

  const Heading = props.titleLevel === 1 ? "h1" : "h2";
  return (
    <div
      ref={errorRef}
      role="alert"
      tabIndex={-1}
      className={`flex flex-col items-start gap-3 border border-coral-vivo/45 bg-coral-vivo/[0.04] p-5 text-nevoa-azul focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acento-principal ${props.className ?? ""}`}
    >
      <Heading className="m-0 text-lg font-bold leading-tight text-branco">
        {props.title ?? "Não foi possível carregar."}
      </Heading>
      <p className="m-0 text-[14px]">{props.message}</p>
      <button
        type="button"
        onClick={props.onRetry}
        className="rounded-full bg-acento-principal px-5 py-2.5 text-[12px] font-bold uppercase tracking-wide text-texto-de-acao transition-colors hover:bg-acento-principal/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-branco"
      >
        Tentar novamente
      </button>
    </div>
  );
}
