import type { ReactNode } from "react";

type Props = {
  tone?: "light" | "muted" | "azulejo";
  labelledBy?: string;
  children: ReactNode;
};

const tones = {
  light: "bg-azul-base",
  muted: "bg-azul-superficie",
  azulejo: "azulejo-bg bg-azul-base", // o azulejo-bg só desenha o padrão: a cor vem do bg-*
};

export default function TeamSection({ tone = "light", labelledBy, children }: Props) {
  return (
    <section aria-labelledby={labelledBy} className={`py-16 md:py-20 ${tones[tone]}`}>
      <div className="mx-auto w-full max-w-6xl px-6">{children}</div>
    </section>
  );
}