import heroFaro from '../assets/hero-faro.webp';
import Eyebrow from './EyeBrow';
import SecundaryButton from './SecundaryButton';
import PrimaryButton from './PrimaryButton';

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
      {/* Grelha do Background */}
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
        <div className="inline-flex items-center">
          <Eyebrow text="LOCAL_HOST: FARO_2027" />
        </div>

        {/* Título Principal com escala fluida forçada */}
        <h1 
            className="font-poppins font-extrabold text-[56px] sm:text-[76px] lg:text-[96px] xl:text-[104px] tracking-[-0.045em] leading-[0.98] bg-clip-text text-transparent"
            style={{ 
                backgroundImage: 'linear-gradient(155deg, #ffffff 65%, rgba(255, 255, 255, 0.75))',
                fontSize: 'clamp(52px, 8.5vw, 108px)' // Força a escala bruta do UI
                }}
            >
                ENEI 2027
        </h1>
        <p className="max-w-[680px] text-lg sm:text-xl text-[#AAB7C9] font-montserrat font-normal leading-relaxed">
          Encontro Nacional de Estudantes de Informática
        </p>

        <div className="inline-flex items-center gap-2 px-3 py-[7px] rounded-full border border-[#00AAFF]/20 bg-[#00AAFF]/[0.12] text-[#d7e3f4] text-[11px] font-semibold font-montserrat tracking-[0.04em] leading-[1.2]">
          <span>8–11 abril 2027 · Faro, Algarve</span>
        </div>

        <div className="flex flex-wrap items-center gap-4 pt-4">
          <SecundaryButton text="Saber mais" />
          <PrimaryButton text="Comprar Bilhete" />
        </div>
      </div>
    </section>
  );
}