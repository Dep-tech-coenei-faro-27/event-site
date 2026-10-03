import React from 'react';
import Eyebrow from './EyeBrow';

interface PathItem {
  number: string;
  category: string;
  title: string;
  description: string;
  linkText: string;
  href: string;
}

const paths: PathItem[] = [
  {
    number: '01',
    category: 'ESTUDANTES',
    title: 'Vive os quatro dias.',
    description: 'Palestras, atividades, alojamento, refeições e toda a experiência ENEI.',
    linkText: 'Comprar bilhete',
    href: '#bilhetes',
  },
  {
    number: '02',
    category: 'EMPRESAS',
    title: 'Liga-te ao talento.',
    description: 'Participa no ecossistema, apresenta oportunidades e cria relações com a comunidade.',
    linkText: 'Conhecer parcerias',
    href: '#parcerias',
  },
  {
    number: '03',
    category: 'COMUNIDADE',
    title: 'Faz parte do encontro.',
    description: 'Conhece a missão, a equipa organizadora e a rede que constrói a edição de Faro.',
    linkText: 'Descobrir o ENEI',
    href: '#sobre',
  },
];

export default function ParticipationSection() {
  return (
    <section className="azulejo-bg relative w-full py-24 bg-[#050d21] text-white">
      <div className="w-full max-w-7xl mx-auto px-6">
        
        {/* Cabeçalho da Secção */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-end pb-16">
          <div className="lg:col-span-7 flex flex-col items-start">
            <Eyebrow text="PARTICIPA" />
            <h2 className="font-poppins font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-[1.1] tracking-tight text-white">
              Um encontro,<br />diferentes percursos.
            </h2>
          </div>

          <div className="lg:col-span-5 flex items-end">
            <p className="font-montserrat text-[#AAB7C9] text-base sm:text-lg leading-relaxed max-w-md">
              Encontra rapidamente a informação certa para a forma como queres participar no ENEI.
            </p>
          </div>
        </div>

        {/* Grelha de 3 Colunas com Linhas Divisórias */}
        <div className="border-t-2 border-b-2  border-[#00AAFF]/20 grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#00AAFF]/20">
          {paths.map((item, index) => (
            <div
              key={index}
              className="py-10 md:py-12 md:px-8 first:pl-0 last:pr-0 flex flex-col justify-between"
            >
              <div>
                {/* Número do Passo */}
                <span className="block text-[#00AAFF] font-montserrat font-bold text-xs tracking-wider mb-8">
                  {item.number}
                </span>

                {/* Categoria / Tag */}
                <span className="block text-[#AAB7C9] font-montserrat font-bold text-[11px] tracking-[0.16em] uppercase mb-3">
                  {item.category}
                </span>

                {/* Título Principal */}
                <h3 className="font-poppins font-extrabold text-2xl lg:text-[26px] text-white leading-tight mb-4">
                  {item.title}
                </h3>

                {/* Descrição */}
                <p className="font-montserrat text-[#AAB7C9] text-sm leading-relaxed mb-8">
                  {item.description}
                </p>
              </div>

              {/* Link de Ação com Seta para Cima e Direita */}
              <a
                href={item.href}
                className="group inline-flex items-center gap-1.5 text-sm font-montserrat font-semibold text-white hover:text-[#00AAFF] transition-colors duration-200 mt-auto"
              >
                <span>{item.linkText}</span>
                <span className="transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5">
                  ↗
                </span>
              </a>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}