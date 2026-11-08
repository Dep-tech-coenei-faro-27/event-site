import type { MouseEvent } from 'react';

/** Ícones dos canais (traço, no mesmo desenho dos outros ícones do site). */
const ICONS = {
  mail: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m4 7 8 6 8-6" />
    </svg>
  ),
  pin: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" />
      <circle cx="12" cy="10" r="2.2" />
    </svg>
  ),
  clock: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  ),
  arrow: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  ),
};

/**
 * «Ainda tens dúvidas?» (`ui-ux/informacao-ajuda`). Os canais são linhas: o email abre a mensagem, o local salta
 * para os mapas desta página (`onShowMap` traz os mapas de volta se uma pesquisa os tiver escondido).
 */
export default function ContactSection({ onShowMap }: { onShowMap?: () => void }) {
  const showMap = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!onShowMap) return;
    event.preventDefault();
    onShowMap();
  };

  return (
    <section className="section section--surface contact-section">
      <div className="container split">
        <div>
          <p className="eyebrow">&lt;CONTACTO /&gt;</p>
          <h2>Ainda tens dúvidas?</h2>
          <p className="lead">Escreve-nos. A equipa ajuda-te.</p>
          <div className="actions">
            <a className="btn btn--primary" href="mailto:geral@eneiconf.pt">
              Contactar
            </a>
          </div>
        </div>
        <div className="contact-channels">
          <h3>Canais de apoio</h3>
          <ul>
            <li>
              <a className="contact-channel" href="mailto:geral@eneiconf.pt">
                {ICONS.mail}
                <span className="contact-channel__text">
                  <small>Email</small>
                  <span>geral@eneiconf.pt</span>
                </span>
                <span className="contact-channel__action">
                  Escrever {ICONS.arrow}
                </span>
              </a>
            </li>
            <li>
              <a className="contact-channel" href="#localizacoes" onClick={showMap}>
                {ICONS.pin}
                <span className="contact-channel__text">
                  <small>Onde</small>
                  <span>Faro, Algarve</span>
                </span>
                <span className="contact-channel__action">
                  Ver mapa {ICONS.arrow}
                </span>
              </a>
            </li>
            <li>
              <div className="contact-channel contact-channel--plain">
                {ICONS.clock}
                <span className="contact-channel__text">
                  <small>Quando</small>
                  <span>Resposta em horário útil</span>
                </span>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
