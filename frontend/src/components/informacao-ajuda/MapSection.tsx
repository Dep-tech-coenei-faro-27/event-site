import { useEffect, useState } from 'react';
import Eyebrow from '../EyeBrow';

const TARGET = new Date('2027-04-01T00:00:00+01:00').getTime();

function useCountdown() {
  const calc = () => Math.max(0, TARGET - Date.now());
  const [ms, setMs] = useState(calc);
  useEffect(() => {
    const t = setInterval(() => setMs(calc()), 1000);
    return () => clearInterval(t);
  }, []);
  const s = Math.floor(ms / 1000);
  return {
    days: String(Math.floor(s / 86400)).padStart(3, '0'),
    hours: String(Math.floor((s % 86400) / 3600)).padStart(2, '0'),
    minutes: String(Math.floor((s % 3600) / 60)).padStart(2, '0'),
    seconds: String(s % 60).padStart(2, '0'),
  };
}

export default function LocationSection() {
  const c = useCountdown();
  const units = [
    [c.days, 'Dias'],
    [c.hours, 'Horas'],
    [c.minutes, 'Minutos'],
    [c.seconds, 'Segundos'],
  ];

  return (
    <section className="azulejo-bg bg-[#081126] py-[clamp(76px,9vw,120px)]">
      <div className="mx-auto w-[min(calc(100%-28px),1180px)] sm:w-[min(calc(100%-40px),1180px)]">
        <div className="mb-11 flex flex-col gap-4 md:flex-row md:items-end md:justify-between md:gap-8">
          <div>
            <Eyebrow text='LOCALIZAÇÃO'/>
            <h2 className="text-[clamp(30px,4vw,52px)] font-semibold leading-[1.06] tracking-[-0.045em] text-white">
              Encontramo-nos em Gambelas.
            </h2>
          </div>
          <p className="max-w-[560px] text-[clamp(17px,2vw,20px)] text-[#b1bccd]">
            O Campus de Gambelas da Universidade do Algarve recebe os quatro dias do ENEI 2027.
          </p>
        </div>

        <div className="grid border border-[#1ab2ff]/40 bg-[#0a172f] shadow-[0_28px_70px_rgba(0,0,0,0.24)] md:grid-cols-[1.2fr_0.8fr]">
          <div className="min-h-[330px] bg-[#030710] md:min-h-[560px]">
            <iframe
              title="Mapa do Campus de Gambelas da Universidade do Algarve"
              loading="lazy"
              src="https://www.openstreetmap.org/export/embed.html?bbox=-7.9850%2C37.0378%2C-7.9588%2C37.0524&layer=mapnik&marker=37.045102%2C-7.971998"
              className="block h-full min-h-[330px] w-full border-0 [filter:saturate(0.72)_contrast(0.94)_brightness(0.86)] md:min-h-[560px]"
            />
          </div>

          <div className="grid grid-rows-[auto_1fr] border-t border-[#1ab2ff]/40 md:border-l md:border-t-0">
            <div
              role="timer"
              aria-label="Contagem decrescente para o início do ENEI 2027"
              className="border-b border-[#1ab2ff]/40 bg-gradient-to-br from-[#1ab2ff]/10 to-transparent px-7 pb-9 pt-8 lg:px-12"
            >
              <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.16em] text-[#23caff]">&lt;COUNTDOWN /&gt;</p>
              <p className="mb-6 text-[clamp(18px,2vw,24px)] font-bold leading-snug text-white">Até ao início do ENEI 2027</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {units.map(([value, label]) => (
                  <div key={label} className="border border-white/10 bg-[#03070d]/45 px-1.5 pb-3 pt-3.5 text-center">
                    <strong className="block text-[clamp(23px,3vw,36px)] font-bold leading-none tracking-tight tabular-nums text-white">
                      {value}
                    </strong>
                    <span className="mt-2 block text-[8px] font-bold uppercase tracking-[0.08em] text-[#8796a9]">{label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid content-center px-7 py-10 lg:px-12">
              <p className="mb-2.5 text-[10px] font-bold uppercase tracking-[0.13em] text-[#23caff]">Recinto principal</p>
              <h3 className="text-[clamp(25px,3vw,36px)] font-semibold leading-[1.06] tracking-[-0.045em] text-white">
                Universidade do Algarve
              </h3>
              <p className="mt-3.5 text-[#b1bccd]">
                Campus de Gambelas<br />8005-139 Faro, Portugal
              </p>
              <dl className="my-7 grid grid-cols-1 gap-4 border-y border-white/10 py-5 sm:grid-cols-2">
                <div>
                  <dt className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#8796a9]">Data</dt>
                  <dd className="mt-2 text-[13px] text-white">1–4 abril 2027</dd>
                </div>
                <div>
                  <dt className="text-[9px] font-bold uppercase tracking-[0.12em] text-[#8796a9]">Campus</dt>
                  <dd className="mt-2 text-[13px] text-white">Gambelas · Faro</dd>
                </div>
              </dl>
              <a
                href="https://www.google.com/maps/search/?api=1&query=37.045102%2C-7.971998"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-[46px] w-fit items-center justify-center rounded-full bg-[#1ab2ff] px-6 text-sm font-bold text-[#02101c] transition hover:-translate-y-0.5 hover:bg-[#23caff]"
              >
                Obter direções
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}