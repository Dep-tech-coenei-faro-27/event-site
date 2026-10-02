import React from 'react';
import Eyebrow from './EyeBrow';

interface DetailCard {
  label: string;
  description: string;
}

const details: DetailCard[] = [
  {
    label: 'RECINTO',
    description: 'Atividades principais no Campus das Gambelas.',
  },
  {
    label: 'ALIMENTAÇÃO',
    description: 'Refeições servidas na cantina do campus.',
  },
  {
    label: 'ALOJAMENTO',
    description: 'Alojamento coletivo para participantes.',
  },
  {
    label: 'MOBILIDADE',
    description: 'Rede dedicada de transporte entre pontos do evento.',
  },
];

export default function ExperienceSection() {
  return (
    <section className="relative w-full py-24 bg-[#030917] text-white">
      <div className="w-full max-w-7xl mx-auto px-6 flex flex-col gap-6">
        
        {/* Bloco Superior: Manifesto de Experiência */}
        <div className="relative p-8 sm:p-12 lg:p-16 rounded-2xl border border-[#00AAFF]/20 border-l-4 border-l-[#00AAFF] bg-[#051126]/60 backdrop-blur-sm">
          <Eyebrow text="EXPERIÊNCIA" />

          <h2 className="font-poppins font-bold text-2xl sm:text-3xl lg:text-4xl text-white leading-snug lg:leading-[1.25] tracking-tight max-w-5xl mb-10">
            Um encontro que combina aprendizagem, competição, cultura académica algarvia e uma plataforma de gamificação para manter toda a comunidade ligada.
          </h2>

          <span className="block text-[#00AAFF] font-montserrat font-bold text-xs tracking-[0.16em] uppercase">
            VISÃO ENEI FARO 2027
          </span>
        </div>

        {/* Bloco Inferior: 4 Cartões de Logística */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {details.map((item, index) => (
            <div
              key={index}
              className="p-6 sm:p-7 rounded-2xl border border-[#00AAFF]/20 border-t-2 border-t-[#00AAFF] bg-[#051126]/60 backdrop-blur-sm flex flex-col justify-start"
            >
              <span className="text-[#00AAFF] font-montserrat font-bold text-xs tracking-[0.16em] uppercase mb-4">
                {item.label}
              </span>
              <p className="font-montserrat text-[#AAB7C9] text-sm leading-relaxed">
                {item.description}
              </p>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}