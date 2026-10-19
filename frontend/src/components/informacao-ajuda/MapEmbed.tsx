import { useState } from 'react';
import { Link } from 'react-router-dom';

interface MapEmbedProps {
  src: string;
  title: string;
  privacyHref?: string;
}

/**
 * Mapa do OpenStreetMap só depois de a pessoa o pedir: carregá-lo partilha o endereço IP com a OpenStreetMap
 * Foundation, por isso não há pedido a terceiros antes do clique (o protótipo carregava-o logo).
 */
export default function MapEmbed({ src, title, privacyHref = '/privacidade' }: MapEmbedProps) {
  const [loaded, setLoaded] = useState(false);

  if (loaded) return <iframe title={title} loading="lazy" src={src} />;

  return (
    <div className="map-consent">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" />
        <circle cx="12" cy="9.5" r="2.5" />
      </svg>
      <p>
        Este mapa é fornecido pelo OpenStreetMap. Ao carregá-lo, o teu endereço IP é partilhado com a OpenStreetMap
        Foundation. Consulta a <Link to={privacyHref}>Política de Privacidade</Link>.
      </p>
      <button type="button" className="btn btn--primary" onClick={() => setLoaded(true)}>
        Carregar mapa
      </button>
    </div>
  );
}
