import React from 'react';
import heroFaro from '../assets/hero-faro.webp'; // ou do teu caminho em assets

export default function Hero() {
  return (
    <section
      className="relative w-full grid items-center overflow-clip border-b border-white/10"
      style={{
        minHeight: 'min(760px, calc(100vh - var(--nav, 80px)))',
        backgroundImage: `
          linear-gradient(
            90deg,
            rgba(5, 13, 33, 0.96) 0%,
            rgba(5, 13, 33, 0.74) 56%,
            rgba(5, 13, 33, 0.88) 100%
          ),
          url(${heroFaro})
        `,
        backgroundPosition: 'center',
        backgroundSize: 'cover',
      }}
    >
      {/* Grelha do Backround*/}
      <div
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0, 170, 255, 0.045) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 170, 255, 0.035) 1px, transparent 1px)
          `,
          backgroundSize: '76px 76px',
          WebkitMaskImage: 'linear-gradient(to bottom, black, transparent 78%)',
          maskImage: 'linear-gradient(to bottom, black, transparent 78%)',
        }}
      />

      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 py-[90px] flex flex-col items-start gap-6">
        <div className="inline-flex items-center gap-2 px-3 py-[7px] rounded-full border border-[#00AAFF]/20 bg-[#00AAFF]/[0.12] text-[#d7e3f4] text-[11px] font-semibold font-montserrat tracking-[0.04em] leaoding-[1.2]">
            {/*TODO: criar uma Componente para esta Tag para futuramente conseguirmos reutilizar nas restantes páginas*/}
            <span>&lt;LOCAL_HOST: FARO_2027 /&gt;</span>
        </div>

        <h1 className="max-w-[880px] font-poppins font-extrabold text-4xl sm:text-5xl lg:text-6xl tracking-tight bg-clip-text text-transparent"
          style={{ backgroundImage: 'linear-gradient(155deg, #ffffff 50%, rgba(255, 255, 255, 0.62))',}}
        >
          ENEI 2027
        </h1>

        <p className="max-w-[680px] text-lg sm:text-xl text-[#AAB7C9] font-montserrat font-normal leading-relaxed">
            Encontro Nacional de Estudantes de Informática
        </p>

        <div className="inline-flex items-center gap-2 px-3 py-[7px] rounded-full border border-[#00AAFF]/20 bg-[#00AAFF]/[0.12] text-[#d7e3f4] text-[11px] font-semibold font-montserrat tracking-[0.04em] leaoding-[1.2]">
            <span>8–11 abril 2027 · Faro, Algarve</span>
        </div>

        <div className="flex flex-wrap items-center gap-4 pt-4">
            <button type="button" className="px-6 py-3 rounded-xl border border-white/20 bg-white/5 hover:bg-white/10 hover:border-white/40 text-[#FFFFFF] font-montserrat font-semibold text-sm sm:text-base transition-all duration-200 backdrop-blur-sm">
                Saber Mais
            </button>

            <button type="button" className="px-6 py-3 rounded-xl bg-[#1AB2FF] hover:bg-[#23CAFF] text-[#02101C] font-montserrat font-bold text-sm sm:text-base transition-all duration-200 shadow-lg shadow-[#1AB2FF]/25 hover:shadow-[#23CAFF]/35 active:scale-95 cursor-pointer">
                Comprar Bilhete
            </button>
        </div>
      </div>
    </section>
  );
}