import Eyebrow from "../EyeBrow";
import equipaFoto from "../../assets/equipa.webp";

// Dimensões reais da imagem (px) e fração que queres mostrar
const IMG_W = 1920;
const IMG_H = 1080;
const VISIBLE = 0.8; // corta os 20% de baixo

export default function TeamHero() {
  return (
    <header
      style={{ "--hero-ratio": `${IMG_W} / ${IMG_H * VISIBLE}` } as React.CSSProperties}
      className="relative isolate flex min-h-[30rem] items-end overflow-hidden bg-azul-base pb-10 pt-24 text-white md:min-h-[36rem] md:pb-28 md:[aspect-ratio:var(--hero-ratio)]"
    >
      {/* Imagem de fundo: largura total, ancorada ao topo */}
      <img
        src={equipaFoto}
        alt="Fotografia da equipa organizadora do ENEI 2027 reunida na praia."
        fetchPriority="high"
        className="absolute inset-0 -z-20 h-full w-full object-cover object-top"
      />

      {/* Escurece ligeiramente e desvanece para o fundo da página */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-gradient-to-b from-azul-base/10 via-azul-base/30 to-azul-base"
      />

      <div className="mx-auto w-full max-w-6xl px-4 md:px-6">
        {/* Painel com barra ciano à esquerda */}
        <div className="max-w-3xl border-l-4 border-acento-principal bg-azul-base/75 p-6 backdrop-blur-sm md:p-12">
          <Eyebrow text="EQUIPA" />
          <h1 className="mt-3 text-3xl font-bold sm:text-4xl md:text-6xl">
            As pessoas por trás do ENEI 2027.
          </h1>
          <p className="mt-4 text-base text-cinza-texto md:mt-6 md:text-lg">
            Uma estrutura organizada por áreas de especialidade para transformar
            ambição estudantil numa experiência nacional.
          </p>
        </div>
      </div>
    </header>
  );
}