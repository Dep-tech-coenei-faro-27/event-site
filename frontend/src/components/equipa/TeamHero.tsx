import Eyebrow from "../EyeBrow";
import equipaFoto from "../../assets/equipa.webp";

// Dimensões reais da imagem (px) e fração que queres mostrar
const IMG_W = 1920;
const IMG_H = 1080;
const VISIBLE = 0.8; // corta os 20% de baixo

export default function TeamHero() {
  return (
    <header
      style={{ aspectRatio: `${IMG_W} / ${IMG_H * VISIBLE}` }}
      className="relative isolate flex flex-col justify-center overflow-hidden bg-azul-base py-20 text-white"
    >
      {/* Imagem de fundo: largura total, ancorada ao topo */}
      <img
        src={equipaFoto}
        alt="Fotografia da equipa organizadora do ENEI 2027 reunida na praia."
        fetchPriority="high"
        className="absolute inset-0 -z-20 h-full w-full object-cover object-top"
      />
      {/* Camada escura */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-gradient-to-r from-azul-base via-azul-base/80 to-azul-base/30"
      />

      <div className="mx-auto w-full max-w-6xl px-6">
        <Eyebrow text="EQUIPA" />
        <h1 className="mt-3 max-w-3xl text-4xl font-bold md:text-6xl">
          As pessoas por trás do ENEI 2027.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-cinza-texto">
          Uma estrutura organizada por áreas de especialidade para transformar
          ambição estudantil numa experiência nacional.
        </p>
      </div>
    </header>
  );
}