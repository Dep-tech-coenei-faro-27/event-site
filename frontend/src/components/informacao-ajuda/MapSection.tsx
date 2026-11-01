import { useEffect, useState } from 'react';
import { EVENT_DATES, EVENT_START } from '../../data/Event';
import MapEmbed from './MapEmbed';
import canteen from '../../assets/cantina-gambelas-ualg.webp';

const TARGET = EVENT_START.getTime();

function useCountdown() {
  const calc = () => Math.max(0, TARGET - Date.now());
  const [ms, setMs] = useState(calc);
  useEffect(() => {
    const timer = setInterval(() => setMs(calc()), 1000);
    return () => clearInterval(timer);
  }, []);
  const s = Math.floor(ms / 1000);
  return {
    started: ms === 0,
    units: [
      [String(Math.floor(s / 86400)).padStart(3, '0'), 'Dias'],
      [String(Math.floor((s % 86400) / 3600)).padStart(2, '0'), 'Horas'],
      [String(Math.floor((s % 3600) / 60)).padStart(2, '0'), 'Minutos'],
      [String(s % 60).padStart(2, '0'), 'Segundos'],
    ] as const,
  };
}

const directions = (query: string) => `https://www.google.com/maps/search/?api=1&query=${query}`;

/** Os dois lugares do ENEI e a contagem decrescente (`ui-ux/informacao-ajuda`). */
export default function LocationSection() {
  const { started, units } = useCountdown();

  return (
    <section className="section section--surface event-location" id="localizacoes">
      <div className="container">
        <div className="section-heading">
          <div>
            <p className="eyebrow">&lt;LOCALIZAÇÕES /&gt;</p>
            <h2>Onde acontece. Onde ficas.</h2>
          </div>
          <p className="lead">
            As atividades decorrem nas Gambelas. O alojamento coletivo fica na Escola Secundária Tomás Cabreira.
          </p>
        </div>

        <div className="location-grid">
          <article className="location-card">
            <div className="location-card__visual">
              <MapEmbed
                title="Mapa do Campus de Gambelas da Universidade do Algarve"
                src="https://www.openstreetmap.org/export/embed.html?bbox=-7.9850%2C37.0378%2C-7.9588%2C37.0524&layer=mapnik&marker=37.045102%2C-7.971998"
              />
              <span className="location-card__number">01</span>
            </div>
            <div className="location-card__content">
              <p className="location-card__label">Recinto do evento</p>
              <h3>Universidade do Algarve</h3>
              <p>
                Campus de Gambelas
                <br />
                8005-139 Faro, Portugal
              </p>
              <dl className="location-card__facts">
                <div>
                  <dt>Função</dt>
                  <dd>Atividades e programa</dd>
                </div>
                <div>
                  <dt>Data</dt>
                  <dd>{EVENT_DATES}</dd>
                </div>
              </dl>
              <a
                className="btn btn--primary"
                href={directions('37.045102%2C-7.971998')}
                target="_blank"
                rel="noopener noreferrer"
              >
                Obter direções
              </a>
            </div>
          </article>

          <article className="location-card location-card--stay">
            <div className="location-card__visual">
              <MapEmbed
                title="Mapa da Escola Secundária Tomás Cabreira"
                src="https://www.openstreetmap.org/export/embed.html?bbox=-7.9358%2C37.0116%2C-7.9190%2C37.0210&layer=mapnik&marker=37.01630042%2C-7.927375733"
              />
              <span className="location-card__number">02</span>
            </div>
            <div className="location-card__content">
              <p className="location-card__label">Alojamento</p>
              <h3>Escola Secundária Tomás Cabreira</h3>
              <p>
                Rua Manuel de Arriaga, n.º 2
                <br />
                8000-334 Faro, Portugal
              </p>
              <dl className="location-card__facts">
                <div>
                  <dt>Função</dt>
                  <dd>Alojamento coletivo</dd>
                </div>
                <div>
                  <dt>Acesso</dt>
                  <dd>Experiência completa</dd>
                </div>
              </dl>
              <p className="location-card__notice">
                Receberás os horários de entrada e a lista do que deves levar antes do evento.
              </p>
              <a
                className="btn btn--primary"
                href={directions('37.01630042%2C-7.927375733')}
                target="_blank"
                rel="noopener noreferrer"
              >
                Obter direções
              </a>
            </div>
          </article>
        </div>

        <article className="meal-location" aria-labelledby="meal-location-title">
          <figure>
            <img src={canteen} alt="Sala de refeições da cantina das Gambelas, com mesas e cadeiras azuis" width={2560} height={1440} loading="lazy" />
            <figcaption>Fotografia: UAlg</figcaption>
          </figure>
          <div>
            <p className="eyebrow">Refeições</p>
            <h3 id="meal-location-title">À mesa nas Gambelas.</h3>
            <p>As refeições são servidas na cantina do campus. Consulta o teu bilhete para saberes se estão incluídas.</p>
          </div>
        </article>

        <div className="countdown location-countdown" role="timer" aria-label="Contagem decrescente para o início do ENEI 2027">
          <div>
            <p className="eyebrow">&lt;CONTAGEM DECRESCENTE /&gt;</p>
            <p className="countdown__intro">{started ? 'O ENEI 2027 já começou.' : 'Até ao início do ENEI 2027'}</p>
          </div>
          <div className="countdown__grid">
            {units.map(([value, label]) => (
              <div key={label}>
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
