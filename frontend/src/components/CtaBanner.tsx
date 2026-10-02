import React from 'react';

export default function CtaBanner() {
  return (
    <section className="relative w-full py-20 bg-[#030917] text-white">
      <div className="w-full max-w-7xl mx-auto px-6">
        
        {/* Caixa Principal Azul com Cantos Arredondados */}
        <div
          className="relative overflow-hidden rounded-[32px] sm:rounded-[40px] bg-gradient-to-r from-[#00A3FF] to-[#0088FF] p-8 sm:p-14 lg:p-16 text-white shadow-2xl shadow-[#00A3FF]/20"
          style={{
            /* Se tiveres o padrão de fundo em SVG/PNG, aplica-o aqui */
            // backgroundImage: "url('/caminho-para-padrao.svg'), linear-gradient(90deg, #00A3FF 0%, #0088FF 100%)",
            // backgroundRepeat: 'repeat',
          }}
        >
          {/* Marca d'água / Padrão decorativo sutil à direita */}
          <div className="pointer-events-none absolute -right-8 -bottom-10 opacity-15 select-none hidden md:block">
            <svg
              className="w-72 h-72 lg:w-96 lg:h-96 text-white"
              viewBox="0 0 200 200"
              fill="currentColor"
            >
              <path d="M100 0 L120 40 L160 50 L130 80 L140 120 L100 100 L60 120 L70 80 L40 50 L80 40 Z" />
            </svg>
          </div>

          <div className="relative z-10 max-w-2xl flex flex-col items-start">
            {/* Tag / Eyebrow em formato código */}
            <span className="inline-block text-white/90 font-montserrat font-bold text-xs tracking-[0.16em] uppercase mb-4">
              &lt;ENEI_2027 /&gt;
            </span>

            {/* Título Principal */}
            <h2 className="font-poppins font-extrabold text-3xl sm:text-5xl lg:text-6xl text-white leading-[1.1] tracking-tight mb-4">
              Prepara-te para fazer parte.
            </h2>

            {/* Descrição */}
            <p className="font-montserrat text-white/90 text-base sm:text-lg leading-relaxed mb-8 max-w-xl">
              Escolhe o teu bilhete e consulta tudo o que precisas para preparar os quatro dias.
            </p>

            {/* Ações / Botões */}
            <div className="flex flex-wrap items-center gap-4">
              {/* Botão Escuro Sólido */}
              <button
                type="button"
                className="min-h-[46px] px-7 py-0 inline-flex items-center justify-center rounded-full bg-[#050D21] hover:bg-[#081635] text-white font-montserrat font-bold text-sm transition-all duration-200 shadow-lg shadow-black/25 active:scale-95 cursor-pointer"
              >
                Comprar bilhete
              </button>

              {/* Botão Escuro com Contorno / Vidro */}
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