import { useState } from 'react';
import FaqSection from '../components/informacao-ajuda/FaqSection';
import LocationSection from '../components/informacao-ajuda/MapSection';
import ContactSection from '../components/informacao-ajuda/ContactSection';
import Eyebrow from '../components/EyeBrow';
import faroCathedral from '../assets/faro-cathedral.webp';
import { usePageMeta } from "../utils/usePageMeta";


export default function InformacaoAjudaPage() {

    usePageMeta("Informação · ENEI 2027", "Encontra respostas às tuas perguntas sobre o ENEI 2027.");

  const [query, setQuery] = useState('');

  return (
    <main id="conteudo" className="bg-[#050d21] font-[Poppins,system-ui,sans-serif] text-white pt-16">
      <header
        className="grid min-h-[440px] items-center border-b border-white/10 bg-cover bg-[position:center_48%] px-0 py-[78px] text-center sm:min-h-[560px]"
        style={{
          backgroundImage: `linear-gradient(180deg, rgba(5,13,33,.7), rgba(5,13,33,.9)), url('${faroCathedral}')`,
        }}
      >
        <div className="mx-auto w-[min(calc(100%-28px),1180px)] sm:w-[min(calc(100%-40px),1180px)]">
          <Eyebrow text="AJUDA" />
          <h1 className="mx-auto max-w-[1000px] text-[clamp(42px,6vw,70px)] font-semibold leading-[1.06] tracking-[-0.045em]">
            Como podemos ajudar?
          </h1>
          <p className="mx-auto mt-5 max-w-[720px] text-[clamp(17px,2vw,20px)] text-white/80">
            Encontra respostas às tuas perguntas sobre o ENEI 2027.
          </p>

          <label className="relative mx-auto mt-8 block max-w-[820px]">
            <span className="sr-only">Pesquisar perguntas</span>
            <svg
              viewBox="0 0 24 24"
              aria-hidden="true"
              className="pointer-events-none absolute left-6 top-1/2 h-5 w-5 -translate-y-1/2 fill-none stroke-[#1ab2ff] stroke-2"
              strokeLinecap="round"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m16 16 5 5" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Pesquisa uma pergunta…"
              autoComplete="off"
              className="h-[58px] w-full rounded-full border-2 border-[#1ab2ff]/40 bg-[#0a172f]/90 pl-[58px] pr-5 text-white outline-none placeholder:text-[#8796a9] focus:border-[#1ab2ff] focus:ring-4 focus:ring-[#1ab2ff]/15 sm:h-16"
            />
          </label>
        </div>
      </header>

      <LocationSection />
      <FaqSection query={query} />
      <ContactSection />
    </main>
  );
}