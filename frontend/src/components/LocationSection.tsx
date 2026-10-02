import React from 'react';
import Eyebrow from './EyeBrow';
import faroMarinaImg from '../assets/faro-baixa.webp'; // Ou a imagem correspondente da marina

export default function LocationSection() {
  return (
    <section className="relative w-full py-24 bg-[#030917] text-white">
      <div className="w-full max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          
          {/* Coluna Esquerda: Imagem com cantos estilizados */}
          <div className="lg:col-span-6">
            <div className="relative overflow-hidden rounded-2xl rounded-tl-[80px] sm:rounded-tl-[100px] border border-[#00AAFF]/20 shadow-2xl shadow-black/50">
              <img
                src={faroMarinaImg}
                alt="Marina de Faro e centro histórico"
                className="w-full h-[360px] sm:h-[420px] object-cover object-center"
              />
            </div>
          </div>

          {/* Coluna Direita: Informação textual */}
          <div className="lg:col-span-6 flex flex-col items-start">
            <Eyebrow text="FARO, ALGARVE" />

            <h2 className="font-poppins font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-[1.1] tracking-tight text-white mb-6">
              Uma cidade feita<br />para receber.
            </h2>

            <p className="font-montserrat text-[#AAB7C9] text-base sm:text-lg leading-relaxed max-w-lg mb-8">
              Faro combina vida académica, acessibilidade, património e a identidade única da Ria Formosa.
            </p>

            <button
              type="button"
              className="min-h-[44px] px-6 py-0 inline-flex items-center justify-center rounded-full border border-white/20 bg-white/5 hover:border-white/40 hover:bg-white/10 text-white font-montserrat font-semibold text-sm transition-all duration-200 cursor-pointer active:scale-95"
            >
              Descobrir Faro
            </button>
          </div>

        </div>
      </div>
    </section>
  );
}