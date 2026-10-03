import React from 'react';

export default function CtaBanner() {
  return (
    <section className="relative w-full py-20 bg-[#050d21] text-white">
      <div className="w-full max-w-7xl mx-auto px-6">
        
        {/* Caixa Principal Azul (mantém o gradiente) */}
        <div className="azulejo-bg relative overflow-hidden rounded-[32px] sm:rounded-[40px] bg-gradient-to-r bg-[#00A3FF] p-8 sm:p-14 lg:p-16 text-white shadow-2xl shadow-[#00A3FF]/20 [&::before]:!opacity-25">
          
          {/* O azulejo fica aqui, desenhado POR CIMA da cor azul */}
          <div className="absolute pointer-events-none z-[1] " />

          {/* Conteúdo à frente de tudo (z-10) */}
          <div className="relative z-10 max-w-2xl flex flex-col items-start">
            <span className="inline-block text-white/90 font-montserrat font-bold text-xs tracking-[0.16em] uppercase mb-4">
              &lt;ENEI_2027 /&gt;
            </span>

            <h2 className="font-poppins font-extrabold text-3xl sm:text-5xl lg:text-6xl text-white leading-[1.1] tracking-tight mb-4">
              Prepara-te para fazer parte.
            </h2>

            <p className="font-montserrat text-white/90 text-base sm:text-lg leading-relaxed mb-8 max-w-xl">
              Escolhe o teu bilhete e consulta tudo o que precisas para preparar os quatro dias.
            </p>

            <div className="flex flex-wrap items-center gap-4">
              <button
                type="button"
                className="min-h-[46px] px-7 py-0 inline-flex items-center justify-center rounded-full bg-[#050D21] hover:bg-[#081635] text-white font-montserrat font-bold text-sm transition-all duration-200 shadow-lg shadow-black/25 active:scale-95 cursor-pointer"
              >
                Comprar bilhete
              </button>

              <button
                type="button"
                className="min-h-[46px] px-7 py-0 inline-flex items-center justify-center rounded-full border border-white/30 bg-[#050D21]/30 hover:bg-[#050D21]/50 hover:border-white/50 text-white font-montserrat font-bold text-sm transition-all duration-200 backdrop-blur-sm active:scale-95 cursor-pointer"
              >
                Tenho dúvidas
              </button>
            </div>
          </div>

        </div>

      </div>
    </section>
  );
}