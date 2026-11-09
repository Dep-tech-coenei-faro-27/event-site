import { EVENT_DATES_SHORT } from '../data/Event';
import { TICKET_NAMES } from '../data/Tickets';
import { Link } from 'react-router-dom';

export default function QuickInfo() {
  const stats = [
    {
      label: 'DATA',
      title: EVENT_DATES_SHORT,
      subtitle: '2027 · Quinta-feira a domingo',
    },
    {
      label: 'LOCAL',
      title: 'Faro, Algarve',
      subtitle: 'Universidade do Algarve',
    },
    {
      label: 'BILHETES',
      title: `${Object.keys(TICKET_NAMES).length} modalidades`,
      subtitle: 'Ver bilhetes',
      to: '/bilhetes',
    },
  ];

  return (
    <div className="container stats-overlap relative z-20">
      <div className="grid grid-cols-1 md:grid-cols-3 rounded-2xl border-2 border-[#00AAFF]/20 bg-[#050D21]/90 backdrop-blur-md overflow-hidden divide-y md:divide-y-0 md:divide-x divide-[#00AAFF]/15 shadow-2xl shadow-black/40">
        {stats.map((item, index) => (
          <div key={index} className="quick-info__item px-8 pt-[18px] pb-6 flex flex-col items-center text-center">
            <span className="quick-info__label text-[#00AAFF] font-montserrat font-bold text-xs tracking-[0.16em] uppercase mb-[26px]">
              {item.label}
            </span>
            <span className="text-white font-poppins font-extrabold text-2xl lg:text-3xl mb-1">
              {item.title}
            </span>
            <span className="text-[#AAB7C9] font-montserrat text-sm">
              {item.to ? <Link to={item.to} className="underline underline-offset-4 hover:text-white">{item.subtitle}</Link> : item.subtitle}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
