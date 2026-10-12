import { useState } from 'react';
import { Link } from 'react-router-dom';

interface MapEmbedProps {
  src: string;
  title: string;
  privacyHref?: string;
}

export default function MapEmbed({ src, title, privacyHref = '/privacidade' }: MapEmbedProps) {
  const [loaded, setLoaded] = useState(false);

  if (loaded) {
    return (
      <iframe
        title={title}
        src={src}
        className="block h-full min-h-[330px] w-full border-0 [filter:saturate(0.72)_contrast(0.94)_brightness(0.86)] md:min-h-[560px]"
      />
    );
  }

  return (
    <div className="flex h-full min-h-[330px] flex-col items-center justify-center gap-5 px-6 py-10 text-center md:min-h-[560px]">
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
        className="h-10 w-10 fill-none stroke-[#1ab2ff] stroke-[1.7] [stroke-linecap:round] [stroke-linejoin:round]"
      >
        <path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" />
        <circle cx="12" cy="9.5" r="2.5" />
      </svg>

      <p className="max-w-[420px] text-sm text-[#b1bccd]">
        Este mapa é fornecido pelo OpenStreetMap. Ao carregá-lo, o teu endereço IP é partilhado com a
        OpenStreetMap Foundation. Consulta a{' '}
        <Link to={privacyHref} className="text-[#23caff] underline underline-offset-4 hover:text-white">
          Política de Privacidade
        </Link>
        .
      </p>

      <button
        type="button"
        onClick={() => setLoaded(true)}
        className="inline-flex min-h-[46px] items-center justify-center rounded-full bg-[#1ab2ff] px-6 text-sm font-bold text-[#02101c] transition hover:-translate-y-0.5 hover:bg-[#23caff]"
      >
        Carregar mapa
      </button>
    </div>
  );
}