export default function QuickInfo() {
  const stats = [
    {
      label: 'DATA',
      title: '8–11 Abr',
      subtitle: '2027 · Quinta a domingo',
    },
    {
      label: 'LOCAL',
      title: 'Faro, Algarve',
      subtitle: 'Universidade do Algarve',
    },
    {
      label: 'BILHETES',
      title: 'ENEI 2027',
      subtitle: 'Consulta a página de bilhetes',
    },
  ];

  return (
    <div className="w-full max-w-7xl mx-auto px-6 -mt-12 relative z-20">
      <div className="grid grid-cols-1 md:grid-cols-3 rounded-2xl border-2 border-[#00AAFF]/20 bg-[#050D21]/90 backdrop-blur-md overflow-hidden divide-y md:divide-y-0 md:divide-x divide-[#00AAFF]/15 shadow-2xl shadow-black/40">
        {stats.map((item, index) => (
          <div key={index} className="p-8 flex flex-col items-center text-center">
            <span className="text-[#00AAFF] font-montserrat font-bold text-xs tracking-[0.16em] uppercase mb-2">
              {item.label}
            </span>
            <span className="text-white font-poppins font-extrabold text-2xl lg:text-3xl mb-1">
              {item.title}
            </span>
            <span className="text-[#AAB7C9] font-montserrat text-sm">
              {item.subtitle}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}