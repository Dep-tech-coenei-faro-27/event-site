import { useState, type KeyboardEvent } from "react";
import "../agenda.css";
import "../agenda.overrides.css";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";
import {
  AGENDA,
  AGENDA_DAYS,
  AGENDA_UTC_OFFSET,
  itemsOfDay,
  timeOf,
  type AgendaDay,
  type AgendaItem,
  type AgendaSpeaker,
} from "../content/agenda";

const DAYS = AGENDA_DAYS.map((d) => d.key);
type Day = AgendaDay["key"];

const speakerPhotos = import.meta.glob("../assets/speakers/*", { eager: true, query: "?url", import: "default" }) as Record<string, string>;

function Speaker({ speaker }: { speaker: AgendaSpeaker }) {
  const src = speaker.photo ? speakerPhotos[`../assets/speakers/${speaker.photo}`] : undefined;
  return (
    <p className="schedule-item__meta schedule-item__speaker">
      {src && <img src={src} alt={speaker.photoAlt ?? ""} width={40} height={40} loading="lazy" />}
      <span>
        <strong>{speaker.name}</strong>
        {speaker.company && <> · {speaker.company}</>}
      </span>
    </p>
  );
}

/** `ui-ux/agenda/index.html` no React. CSS gerado em `agenda.css` (ver `scripts/ui-port/genpage.py`). */
export default function Agenda({ items = AGENDA }: { items?: AgendaItem[] }) {
  useBodyPage("agenda");
  const [day, setDay] = useState<Day>("quinta");

  // Setas, Início e Fim passam de um dia ao outro, como num separador acessível.
  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    const index = DAYS.indexOf(day);
    const next =
      event.key === "ArrowRight" ? (index + 1) % DAYS.length
      : event.key === "ArrowLeft" ? (index + DAYS.length - 1) % DAYS.length
      : event.key === "Home" ? 0
      : event.key === "End" ? DAYS.length - 1
      : -1;
    if (next < 0) return;
    event.preventDefault();
    setDay(DAYS[next]);
    document.getElementById(`tab-${DAYS[next]}`)?.focus();
  };

  usePageMeta('Agenda · ENEI 2027', 'Programa, atividades e experiências do ENEI 2027.');

  return (
    <>

      <header className="page-hero center">
      <div className="container">
      <p className="eyebrow">&lt;PROGRAMA /&gt;</p>
      <h1>Quatro dias para experimentar.</h1>
      <p className="lead">
      Consulta o programa dia a dia e prepara a tua passagem pelo ENEI
      2027.
      </p>
      <div className="date-pill" style={{ margin: "26px auto 0" }}>
      1–4 abril 2027 · Campus das Gambelas
      </div>
      </div>
      </header>
      <section className="section section--surface agenda-schedule-section">
      <div className="container">
      <div className="section-heading">
      <div>
      <p className="eyebrow">&lt;AGENDA POR DIA /&gt;</p>
      <h2>Quatro dias, um programa completo.</h2>
      </div>
      <p className="lead">
      Consulta os principais momentos de cada dia do ENEI 2027.
      </p>
      </div>
      <div className="tabs agenda-day-tabs" role="tablist" aria-label="Dias do programa">
      {AGENDA_DAYS.map((d) => (
      <button className="tab agenda-day-tab" id={`tab-${d.key}`} key={d.key} type="button" role="tab" aria-selected={day === d.key} aria-controls={`agenda-${d.key}`} tabIndex={day === d.key ? 0 : -1} onClick={() => setDay(d.key)} onKeyDown={onTabKey}>
      <span>{d.weekday}</span><strong>{d.short}</strong>
      </button>
      ))}
      </div>
      {AGENDA_DAYS.map((d) => (
      <div className={day === d.key ? "schedule" : "schedule hidden"} id={`agenda-${d.key}`} key={d.key} role="tabpanel" aria-labelledby={`tab-${d.key}`}>
      <p className="schedule-day-label">{d.label}</p>
      {itemsOfDay(items, d).map((item) => (
      <article className="schedule-item" id={item.id} key={item.id}>
      <time dateTime={`${item.start}${AGENDA_UTC_OFFSET}`}>{timeOf(item)}</time>
      <div>
      <h3>{item.title}</h3>
      {item.location && <p className="schedule-item__meta">{item.location}</p>}
      {item.speaker && <Speaker speaker={item.speaker} />}
      </div>
      <span className={`tag tag--${item.tag.tone}`}>{item.tag.label}</span>
      </article>
      ))}
      </div>
      ))}
      </div>
      </section>
      <section className="section section--panel">
      <div className="container split">
      <div>
      <p className="eyebrow">&lt;PLATAFORMA /&gt;</p>
      <h2>O evento continua no teu telemóvel.</h2>
      <p className="lead">
      A experiência digital recompensa a descoberta do recinto, a
      interação com oradores e a visita às bancas dos parceiros.
      </p>
      </div>
      <div className="platform-flow">
      <article className="platform-flow__item">
      <div className="icon icon--sand" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <circle cx="12" cy="9" r="6" />
      <path d="m8.5 14-1 7 4.5-2 4.5 2-1-7M9.5 9l1.5 1.5 3-3" />
      </svg>
      </div>
      <h3>Badges</h3>
      <p>Conquistas associadas à participação e exploração.</p>
      </article>
      <article className="platform-flow__item">
      <div className="icon icon--teal" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="M4 18 10 12l4 4 6-8" />
      <path d="M15 8h5v5" />
      </svg>
      </div>
      <h3>Progressão</h3>
      <p>Moedas virtuais e recompensas por envolvimento.</p>
      </article>
      <article className="platform-flow__item">
      <div className="icon icon--periwinkle" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2M20 14v2M14 20h2M18 18h2v2" />
      </svg>
      </div>
      <h3>Ativações</h3>
      <p>Pontos de interação distribuídos pelo evento.</p>
      </article>
      <article className="platform-flow__item">
      <div className="icon icon--coral" aria-hidden="true">
      <svg viewBox="0 0 24 24" width={24} height={24} aria-hidden="true" focusable="false">
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8z" />
      </svg>
      </div>
      <h3>Comunidade</h3>
      <p>Novas formas de ligar participantes, oradores e empresas.</p>
      </article>
      </div>
      </div>
      </section>

    </>
  );
}
