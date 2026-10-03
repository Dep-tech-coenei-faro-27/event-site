import React from 'react';
import Eyebrow from './EyeBrow';

interface ProgramCardItem {
  title: string;
  description: string;
  icon: React.ReactNode;
  accentColor: string;
  borderColor: string;
  hoverBorder: string;
  glowColor: string;
  iconBg: string;
  iconBorder: string;
}

const programCards: ProgramCardItem[] = [
  {
    title: 'Workshops',
    description: 'Sessões práticas em grupos reduzidos.',
    accentColor: 'text-ciano-digital',
    borderColor: 'border-ciano-digital/30',
    hoverBorder: 'hover:border-ciano-digital/60',
    glowColor: 'from-ciano-digital/30',
    iconBg: 'bg-ciano-digital/10',
    iconBorder: 'border-ciano-digital/30',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    title: 'Palestras',
    description: 'Ideias e experiências de quem está a construir o futuro.',
    accentColor: 'text-coral-suave',
    borderColor: 'border-coral-suave/30',
    hoverBorder: 'hover:border-coral-suave/60',
    glowColor: 'from-coral-suave/30',
    iconBg: 'bg-coral-suave/10',
    iconBorder: 'border-coral-suave/30',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
      </svg>
    ),
  },
  {
    title: 'Networking',
    description: 'Empresas, talento e oportunidades reais.',
    accentColor: 'text-ciano-vivo',
    borderColor: 'border-ciano-vivo/30',
    hoverBorder: 'hover:border-ciano-vivo/60',
    glowColor: 'from-ciano-vivo/30',
    iconBg: 'bg-ciano-vivo/10',
    iconBorder: 'border-ciano-vivo/30',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
  },
  {
    title: 'Convívio',
    description: 'Momentos sociais para tornar a experiência memorável.',
    accentColor: 'text-pervinca',
    borderColor: 'border-pervinca/30',
    hoverBorder: 'hover:border-pervinca/60',
    glowColor: 'from-pervinca/30',
    iconBg: 'bg-pervinca/10',
    iconBorder: 'border-pervinca/30',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
      </svg>
    ),
  },
];

export default function ProgramSection() {
  return (
    <section className="relative w-full pt-20 sm:pt-30 pb-20 bg-azul-base text-branco">
      <div className="w-full max-w-7xl mx-auto px-6">
        
        {/* Cabeçalho */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start pb-8">
          <div className="lg:col-span-7 flex flex-col items-start gap-1">
            <Eyebrow text="PROGRAMA" />
            <h2 className="m-0 mt-1 font-poppins font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-[1.08] tracking-tight text-branco">
              Quatro dias para<br />descobrir.
            </h2>
          </div>

          <div className="lg:col-span-5 flex items-start lg:pt-8">
            <p className="font-montserrat text-nevoa-azul text-base sm:text-lg leading-relaxed max-w-md m-0">
              Explora quatro dias de tecnologia, aprendizagem, networking e comunidade.
            </p>
          </div>
        </div>

        {/* Grelha de 4 Cartões */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 items-stretch">
          {programCards.map((card, index) => (
            <div
              key={index}
              className={`azulejo-bg relative p-4 sm:p-7 rounded-2xl border ${card.borderColor} ${card.hoverBorder} bg-azul-superficie-2/70 backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 flex flex-col justify-between overflow-hidden group shadow-lg`}
            >
              {/* Resplandor superior concentrado na borda */}
              <div
                className={`pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 w-48 h-16 bg-gradient-to-b ${card.glowColor} to-transparent blur-xl opacity-90`}
              />

              {/* Topo do card: Ícone + Título */}
              <div className="relative z-10 flex flex-col items-start">
                <div
                  className={`w-11 h-11 rounded-xl border ${card.iconBorder} ${card.iconBg} ${card.accentColor} flex items-center justify-center mb-6`}
                >
                  {card.icon}
                </div>

                <h3 className="font-poppins font-bold text-xl text-branco mb-2.5 m-0">
                  {card.title}
                </h3>
              </div>

              {/* Base do card: Descrição */}
              <p className="font-montserrat text-nevoa-azul text-sm leading-relaxed relative z-10 m-0 mt-2">
                {card.description}
              </p>
            </div>
          ))}
        </div>

        {/* Botão Ver Agenda */}
        <div className="flex justify-center mt-12">
          <button
            type="button"
            className="px-7 py-3 rounded-full bg-ciano-digital hover:bg-acento-forte text-texto-sobre-ciano font-montserrat font-bold text-sm transition-all duration-200 shadow-md shadow-ciano-digital/20 hover:shadow-acento-forte/30 active:scale-95 cursor-pointer"
          >
            Ver agenda
          </button>
        </div>

      </div>
    </section>
  );
}