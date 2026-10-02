import AboutSectionCard from './AboutSectionCards';
import Eyebrow from './EyeBrow';

export default function AboutSection() {
  const cards = [
    {
      badge: 'PROGRAMA',
      title: 'Aprender e experimentar.',
      text: 'Conteúdo técnico, desafios e cultura académica num só encontro.',
    },
    {
      badge: 'REDE',
      title: 'Criar ligações reais.',
      text: 'Estudantes, comunidades e organizações lado a lado durante quatro dias.',
    },
    {
      badge: 'EDIÇÃO',
      title: 'Uma identidade algarvia.',
      text: 'O ambiente de Faro dá ritmo e contexto à experiência de 2027.',
    },
  ];

  return (
    <section className="relative w-full py-24 bg-[#030917] text-white">
      <div className="w-full max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
        
        {/* Coluna Esquerda: Texto Principal */}
        <div className="lg:col-span-6 flex flex-col items-start">
          <Eyebrow text="18.ª EDIÇÃO" />

          <h2 className="font-poppins font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-[1.15] tracking-tight mb-6">
            O ponto de encontro da próxima geração tecnológica.
          </h2>

          <p className="font-montserrat text-[#AAB7C9] text-base sm:text-lg leading-relaxed mb-8 max-w-xl">
            Quatro dias para ligar estudantes de todo o país às tendências do setor,
            ao ecossistema empresarial e a novas comunidades.
          </p>

          <button
            type="button"
            className="px-7 py-3.5 rounded-full border border-white/20 bg-white/5 hover:bg-white/10 hover:border-white/40 text-white font-montserrat font-semibold text-sm transition-all duration-200 cursor-pointer"
          >
            Conhecer o ENEI
          </button>
        </div>

        {/* Coluna Direita: Cartões com Borda Esquerda */}
        <div className="lg:col-span-6 flex flex-col gap-5">
            <AboutSectionCard />
        </div>

      </div>
    </section>
  );
}