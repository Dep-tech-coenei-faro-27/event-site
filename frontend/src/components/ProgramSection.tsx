import React from 'react';
import Eyebrow from './EyeBrow';

interface ProgramCardItem {
  title: string;
  description: string;
  icon: React.ReactNode;
}

const programCards: ProgramCardItem[] = [
  {
    title: 'Workshops',
    description: 'Sessões práticas em grupos reduzidos.',
    icon: (
      <svg className="w-5 h-5 text-[#00AAFF]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    title: 'Palestras',
    description: 'Ideias e experiências de quem está a construir o futuro.',
    icon: (
      <svg className="w-5 h-5 text-[#00AAFF]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
      </svg>
    ),
  },
  {
    title: 'Networking',
    description: 'Empresas, talento e oportunidades reais.',
    icon: (
      <svg className="w-5 h-5 text-[#00AAFF]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
  },
  {
    title: 'Convívio',
    description: 'Momentos sociais para tornar a experiência memorável.',
    icon: (
      <svg className="w-5 h-5 text-[#00AAFF]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
      </svg>
    ),
  },
];

export default function ProgramSection() {
  return (
    <section className="relative w-full py-24 bg-[#030917] text-white">
      <div className="w-full max-w-7xl mx-auto px-6">
        
        {/* Cabeçalho da Secção */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-end pb-16">
          <div className="lg:col-span-7 flex flex-col items-start">
            <Eyebrow text="PROGRAMA" />
            <h2 className="font-poppins font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-[1.1] tracking-tight text-white">
              Quatro dias para<br />descobrir.
            </h2>
          </div>

          <div className="lg:col-span-5 flex items-end">
            <p className="font-montserrat text-[#AAB7C9] text-base sm:text-lg leading-relaxed max-w-md">
              Explora quatro dias de tecnologia, aprendizagem, networking e comunidade.
            </p>
          </div>
        </div>

        {/* Grelha de 4 Cartões */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {programCards.map((card, index) => (
            <div
              key={index}
              className="relative p-6 sm:p-7 rounded-2xl border border-[#00AAFF]/20 bg-[#051126]/60 backdrop-blur-sm transition-all duration-300 hover:border-[#00AAFF]/50 hover:-translate-y-1 flex flex-col justify-start"
            >
              {/* Ícone */}
              <div className="w-11 h-11 rounded-xl border border-[#00AAFF]/30 bg-[#00AAFF]/10 flex items-center justify-center mb-6">
                {card.icon}
              </div>

              {/* Título */}
              <h3 className="font-poppins font-bold text-xl text-white mb-2.5">
                {card.title}
              </h3>

              {/* Descrição */}
              <p className="font-montserrat text-[#AAB7C9] text-sm leading-relaxed">
                {card.description}
              </p>
            </div>
          ))}
        </div>

        {/* Botão Ver Agenda */}
        <div className="flex justify-center mt-14">
          <button
            type="button"
            className="px-6 py-2.5 rounded-full bg-[#00AAFF] hover:bg-[#23CAFF] text-[#02101C] font-montserrat font-bold text-sm transition-all duration-200 shadow-md shadow-[#00AAFF]/20 hover:shadow-[#23CAFF]/30 active:scale-95 cursor-pointer"
          >
            Ver agenda
          </button>
        </div>

      </div>
    </section>
  );
}