import { useState, type KeyboardEvent } from "react";
import "../agenda.css";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";

const DAYS = ["quinta", "sexta", "sabado", "domingo"] as const;
type Day = (typeof DAYS)[number];

/** `ui-ux/agenda/index.html` no React. CSS gerado em `agenda.css` (ver `scripts/ui-port/genpage.py`). */
export default function Agenda() {
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
      <button className="tab agenda-day-tab" id="tab-quinta" type="button" role="tab" aria-selected={day === "quinta"} aria-controls="agenda-quinta" tabIndex={day === "quinta" ? 0 : -1} onClick={() => setDay("quinta")} onKeyDown={onTabKey}>
      <span>Quinta</span><strong>1 Abr</strong>
      </button>
      <button className="tab agenda-day-tab" id="tab-sexta" type="button" role="tab" aria-selected={day === "sexta"} aria-controls="agenda-sexta" tabIndex={day === "sexta" ? 0 : -1} onClick={() => setDay("sexta")} onKeyDown={onTabKey}>
      <span>Sexta</span><strong>2 Abr</strong>
      </button>
      <button className="tab agenda-day-tab" id="tab-sabado" type="button" role="tab" aria-selected={day === "sabado"} aria-controls="agenda-sabado" tabIndex={day === "sabado" ? 0 : -1} onClick={() => setDay("sabado")} onKeyDown={onTabKey}>
      <span>Sábado</span><strong>3 Abr</strong>
      </button>
      <button className="tab agenda-day-tab" id="tab-domingo" type="button" role="tab" aria-selected={day === "domingo"} aria-controls="agenda-domingo" tabIndex={day === "domingo" ? 0 : -1} onClick={() => setDay("domingo")} onKeyDown={onTabKey}>
      <span>Domingo</span><strong>4 Abr</strong>
      </button>
      </div>
      <div className={day === "quinta" ? "schedule" : "schedule hidden"} id="agenda-quinta" role="tabpanel" aria-labelledby="tab-quinta">
      <p className="schedule-day-label">Quinta-feira · 1 abril</p>
      <article className="schedule-item">
      <time dateTime="2027-04-01T14:00">14:00</time>
      <div><h3>Check-ins</h3></div>
      <span className="tag tag--sand">Check-in</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-01T18:00">18:00</time>
      <div><h3>Sessão de boas-vindas</h3></div>
      <span className="tag tag--cyan">Boas-vindas</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-01T20:00">20:00</time>
      <div><h3>Jantar e arraial académico</h3></div>
      <span className="tag tag--teal">Jantar</span>
      </article>
      </div>
      <div className={day === "sexta" ? "schedule" : "schedule hidden"} id="agenda-sexta" role="tabpanel" aria-labelledby="tab-sexta">
      <p className="schedule-day-label">Sexta-feira · 2 abril</p>
      <article className="schedule-item">
      <time dateTime="2027-04-02T10:00">10:00</time>
      <div><h3>Palestra e workshops #1, #2 e #3</h3></div>
      <span className="tag tag--coral">Palestra / workshop</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T11:00">11:00</time>
      <div><h3>Palestra</h3></div>
      <span className="tag tag--cyan">Palestra</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T12:00">12:00</time>
      <div><h3>Almoço</h3></div>
      <span className="tag tag--teal">Refeição</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T14:00">14:00</time>
      <div><h3>Palestra e workshops #4, #5 e #6</h3></div>
      <span className="tag tag--coral">Palestra / workshop</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T15:00">15:00</time>
      <div><h3>Palestra</h3></div>
      <span className="tag tag--cyan">Palestra</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T16:30">16:30</time>
      <div><h3>Coffee break</h3></div>
      <span className="tag tag--sand">Networking</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T17:00">17:00</time>
      <div><h3>Palestra</h3></div>
      <span className="tag tag--cyan">Palestra</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T18:00">18:00</time>
      <div><h3>Tertúlia</h3></div>
      <span className="tag tag--periwinkle">Tertúlia</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T20:00">20:00</time>
      <div><h3>Jantar</h3></div>
      <span className="tag tag--teal">Refeição</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-02T22:00">22:00</time>
      <div><h3>Atividades noturnas</h3></div>
      <span className="tag tag--periwinkle">Noite</span>
      </article>
      </div>
      <div className={day === "sabado" ? "schedule" : "schedule hidden"} id="agenda-sabado" role="tabpanel" aria-labelledby="tab-sabado">
      <p className="schedule-day-label">Sábado · 3 abril</p>
      <article className="schedule-item">
      <time dateTime="2027-04-03T10:00">10:00</time>
      <div><h3>Palestra e workshops #10, #11 e #12</h3></div>
      <span className="tag tag--coral">Palestra / workshop</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T11:00">11:00</time>
      <div><h3>Palestra</h3></div>
      <span className="tag tag--cyan">Palestra</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T12:00">12:00</time>
      <div><h3>Almoço</h3></div>
      <span className="tag tag--teal">Refeição</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T14:00">14:00</time>
      <div><h3>Palestra e workshops #13, #14 e #15</h3></div>
      <span className="tag tag--coral">Palestra / workshop</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T15:00">15:00</time>
      <div><h3>Palestra</h3></div>
      <span className="tag tag--cyan">Palestra</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T16:30">16:30</time>
      <div><h3>Coffee break</h3></div>
      <span className="tag tag--sand">Networking</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T17:00">17:00</time>
      <div><h3>Palestra</h3></div>
      <span className="tag tag--cyan">Palestra</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T18:00">18:00</time>
      <div><h3>Tertúlia</h3></div>
      <span className="tag tag--periwinkle">Tertúlia</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T20:00">20:00</time>
      <div><h3>Jantar</h3></div>
      <span className="tag tag--teal">Refeição</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-03T22:00">22:00</time>
      <div><h3>Atividades noturnas</h3></div>
      <span className="tag tag--periwinkle">Noite</span>
      </article>
      </div>
      <div className={day === "domingo" ? "schedule" : "schedule hidden"} id="agenda-domingo" role="tabpanel" aria-labelledby="tab-domingo">
      <p className="schedule-day-label">Domingo · 4 abril</p>
      <article className="schedule-item">
      <time dateTime="2027-04-04T10:00">10:00</time>
      <div><h3>Nascer do sol na praia</h3></div>
      <span className="tag tag--sand">Social</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-04T12:00">12:00</time>
      <div><h3>Almoço</h3></div>
      <span className="tag tag--teal">Refeição</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-04T14:00">14:00</time>
      <div><h3>Tertúlia</h3></div>
      <span className="tag tag--periwinkle">Tertúlia</span>
      </article>
      <article className="schedule-item">
      <time dateTime="2027-04-04T16:00">16:00</time>
      <div><h3>Sessão de encerramento</h3></div>
      <span className="tag tag--cyan">Encerramento</span>
      </article>
      </div>
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
