export default function CtaBanner() {
  return (
    <section className="relative w-full py-20 bg-[#050d21] text-white">
      <div className="container">
        
        {/* Caixa principal: degradê do ciano profundo (onde está o texto, contraste ~5,5:1) para o ciano digital */}
        <div className="azulejo-bg relative overflow-hidden rounded-[32px] sm:rounded-[40px] bg-gradient-to-r from-ciano-profundo to-[#0089CF] p-8 sm:p-14 lg:p-16 text-white shadow-xl shadow-black/30 [&::before]:!opacity-[0.24]">
          
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
                className="btn btn--dark"
              >
                Comprar bilhete
              </button>

              <button
                type="button"
                className="btn btn--outline-light"
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