interface CardItem {
  badge: string;
  title: string;
  text: string;
}

const cards: CardItem[] = [
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

export default function AboutSectionCard() {
  return (
    <div className="lg:col-span-6 flex flex-col gap-5">
      {cards.map((card, index) => (
        <div
          key={index}
          className="azulejo-bg relative p-6 sm:p-7 border-l-4 border-l-[#00AAFF] border-y border-r border-[#00AAFF]/20 bg-[#051126]/60 backdrop-blur-sm transition-all hover:bg-[#051126]/90 flex flex-col sm:flex-row items-start gap-4 sm:gap-8"
        >
          {/* Coluna 1: Badge Isolada */}
          <div className="w-28 shrink-0 pt-1">
            <span className="text-[#00AAFF] font-montserrat font-bold text-xs tracking-[0.16em] uppercase">
              {card.badge}
            </span>
          </div>

          {/* Coluna 2: Título e Descrição */}
          <div className="flex flex-col flex-1">
            <h3 className="font-poppins font-bold text-lg sm:text-xl text-white mb-2 leading-snug">
              {card.title}
            </h3>
            <p className="font-montserrat text-[#AAB7C9] text-sm sm:text-base leading-relaxed">
              {card.text}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
} 