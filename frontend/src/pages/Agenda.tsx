import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import portraitPlaceholder from "../assets/portrait-placeholder.svg";
import "../agenda-base.css";
import "../agenda.css";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";
import {
  AGENDA,
  AGENDA_DAYS,
  AGENDA_UTC_OFFSET,
  cardOf,
  endOf,
  itemsOfDay,
  matchesFilter,
  pendingLocation,
  pendingSpeaker,
  timeOf,
  type AgendaDay,
  type AgendaItem,
} from "../content/agenda";

type Filter = "all" | "palestras" | "workshops" | "saved";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "Tudo" },
  { key: "palestras", label: "Palestras" },
  { key: "workshops", label: "Workshops" },
  { key: "saved", label: "Guardados" },
];

export const SAVED_KEY = "enei-agenda-saved";
const DEFAULT_DAY: AgendaDay["key"] = "sexta";

const speakerPhotos = import.meta.glob("../assets/speakers/*", { eager: true, query: "?url", import: "default" }) as Record<string, string>;

const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

/** Tudo o que o cartão mostra, para a pesquisa. */
function searchableText(item: AgendaItem): string {
  const who = item.speaker ? [item.speaker.name, item.speaker.company ?? ""] : [pendingSpeaker(item), "Perfil e organização em breve"];
  return [timeOf(item), endOf(item) ?? "", item.kind, item.title, item.location ?? pendingLocation(item), ...(cardOf(item) === "speaker" ? who : [])].join(" ");
}

function readSaved(items: AgendaItem[]): Set<string> {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(SAVED_KEY) ?? "[]");
    if (Array.isArray(stored)) return new Set(stored.filter((id): id is string => typeof id === "string" && items.some((item) => item.id === id)));
  } catch {
    // A agenda continua a funcionar sem armazenamento.
  }
  return new Set();
}

/** `?dia=sexta` no endereço; sem ele (ou com um valor que não existe) abre a sexta-feira, o primeiro dia completo. */
function dayFromQuery(value: string | null): AgendaDay["key"] {
  return AGENDA_DAYS.find((day) => day.key === value)?.key ?? DEFAULT_DAY;
}

function Portrait({ item }: { item: AgendaItem }) {
  const photo = item.speaker?.photo ? speakerPhotos[`../assets/speakers/${item.speaker.photo}`] : undefined;
  return (
    <img
      src={photo ?? portraitPlaceholder}
      alt={photo ? (item.speaker?.photoAlt ?? "") : "Retrato do orador por anunciar"}
      width={168}
      height={188}
      loading="lazy"
    />
  );
}

interface CardProps {
  item: AgendaItem;
  saved: boolean;
  action: ReactNode;
  onSave: (id: string) => void;
}

function SessionCard({ item, saved, action, onSave }: CardProps) {
  const kind = cardOf(item);
  const end = endOf(item);
  return (
    <li id={item.id} className={`ag-card ag-card--${item.category}${item.tone ? ` ag-card--${item.tone}` : ""}`} data-session={item.id} data-category={item.category}>
      <div className={`ag-card__media${kind === "speaker" ? "" : " ag-card__media--moment"}`} aria-hidden={kind === "speaker" ? undefined : true}>
        {kind === "speaker" && <Portrait item={item} />}
      </div>
      <div className="ag-card__body">
        <div className="ag-card__meta">
          <span className="ag-card__time">
            <time dateTime={`${item.start}${AGENDA_UTC_OFFSET}`}>{timeOf(item)}</time>
            {end && item.end && (
              <>
                {" – "}
                <time dateTime={`${item.end}${AGENDA_UTC_OFFSET}`}>{end}</time>
              </>
            )}
          </span>
          <span className="ag-card__sep" aria-hidden="true"></span>
          <span className="ag-card__kind">{item.kind}</span>
          <button
            className="ag-save"
            type="button"
            aria-label={`${saved ? "Remover dos guardados" : "Guardar sessão"}: ${item.title}`}
            aria-pressed={saved}
            onClick={() => onSave(item.id)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M6 4h12v17l-6-4-6 4Z" />
            </svg>
          </button>
        </div>
        <h3>{item.title}</h3>
        {kind === "speaker" && (
          <p className={`ag-card__who${item.speaker ? "" : " ag-card__who--pending"}`}>
            <strong>{item.speaker ? item.speaker.name : pendingSpeaker(item)}</strong>
            <span> · {item.speaker ? (item.speaker.company ?? "") : "Perfil e organização em breve"}</span>
          </p>
        )}
        <div className="ag-card__foot">
          <p className="ag-card__where">
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" />
              <circle cx="12" cy="10" r="2" />
            </svg>
            {item.location ?? pendingLocation(item)}
          </p>
          {action && (
            <div className="ag-card__action" data-slot="action">
              {action}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

interface AgendaProps {
  items?: AgendaItem[];
  /**
   * O espaço da ação no canto de cada cartão (inscrição, compra…). Devolve o botão desse item, ou nada. Sem isto, o
   * cartão não mostra nenhum botão e o espaço fica reservado, para todos terem a mesma altura.
   */
  renderAction?: (item: AgendaItem) => ReactNode;
}

/** A Agenda: proposta B2 (cartões horizontais), escolhida a 26/10/2026. CSS em `agenda.css` e `agenda-base.css`. */
export default function Agenda({ items = AGENDA, renderAction }: AgendaProps) {
  useBodyPage("agenda");
  usePageMeta("Agenda · ENEI 2027", "Programa, atividades e experiências do ENEI 2027.");

  const [params, setParams] = useSearchParams();
  const day = dayFromQuery(params.get("dia"));
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [saved, setSaved] = useState<Set<string>>(() => readSaved(items));
  const [toast, setToast] = useState<string | null>(null);

  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const filterRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const toastTimer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(toastTimer.current), []);

  const notify = useCallback((message: string) => {
    window.clearTimeout(toastTimer.current);
    setToast(message);
    toastTimer.current = window.setTimeout(() => setToast(null), 2300);
  }, []);

  const selectDay = (key: AgendaDay["key"], focus = false) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("dia", key);
        return next;
      },
      { replace: true },
    );
    if (focus) tabRefs.current[key]?.focus();
  };

  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const count = AGENDA_DAYS.length;
    const next =
      event.key === "ArrowRight" || event.key === "ArrowDown"
        ? (index + 1) % count
        : event.key === "ArrowLeft" || event.key === "ArrowUp"
          ? (index - 1 + count) % count
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? count - 1
              : -1;
    if (next < 0) return;
    event.preventDefault();
    selectDay(AGENDA_DAYS[next].key, true);
  };

  const toggleSaved = (id: string) => {
    const wasSaved = saved.has(id);
    const next = new Set(saved);
    if (wasSaved) next.delete(id);
    else next.add(id);
    setSaved(next);
    try {
      localStorage.setItem(SAVED_KEY, JSON.stringify([...next]));
    } catch {
      // Só nesta visita, se o armazenamento não estiver disponível.
    }
    notify(wasSaved ? "Sessão removida dos guardados." : "Sessão guardada neste dispositivo.");
    // Com o filtro «Guardados», o cartão desaparece ao remover: o foco passa para o filtro.
    if (wasSaved && filter === "saved") window.setTimeout(() => filterRefs.current.saved?.focus(), 0);
  };

  const q = normalize(query.trim());
  const current = AGENDA_DAYS.find((d) => d.key === day) ?? AGENDA_DAYS[1];
  const cards = itemsOfDay(items, current)
    .filter((item) => matchesFilter(item, filter, saved) && normalize(searchableText(item)).includes(q))
    .map((item) => ({ item, action: renderAction?.(item) ?? null }));
  const count = cards.length;
  const savedCount = items.filter((item) => saved.has(item.id)).length;

  const resetFilters = () => {
    setFilter("all");
    setQuery("");
    filterRefs.current.all?.focus();
  };

  return (
    <>
      <header className="page-hero agenda-hero center">
        <div className="container">
          <p className="eyebrow">&lt;AGENDA /&gt;</p>
          <h1>Encontra a tua próxima ideia.</h1>
          <p className="lead">Palestras, workshops e encontros que dão forma ao ENEI 2027. Escolhe o teu dia e faz o teu percurso.</p>
          <div className="date-pill">1–4 abril 2027 · Faro</div>
        </div>
      </header>

      <section className="ag-programme" id="programa" aria-label="Programa por dia">
        <div className="container">
          <p className="eyebrow">&lt;AGENDA POR DIA /&gt;</p>
          <h2>Quatro dias, um programa completo.</h2>
          <p className="lead">Escolhe o dia e filtra por tipo de sessão.</p>

          <div role="tablist" aria-label="Dias do programa" className="ag-days">
            {AGENDA_DAYS.map((d, index) => (
              <button
                key={d.key}
                ref={(el) => {
                  tabRefs.current[d.key] = el;
                }}
                type="button"
                role="tab"
                id={`ag-tab-${d.key}`}
                className="ag-day"
                aria-selected={d.key === day}
                aria-controls="ag-panel"
                tabIndex={d.key === day ? 0 : -1}
                onClick={() => selectDay(d.key)}
                onKeyDown={(event) => onTabKey(event, index)}
              >
                <small>{d.tab}</small>
                <strong>{d.short}</strong>
              </button>
            ))}
          </div>

          <div className="ag-toolbar">
            <div className="ag-filters" role="group" aria-label="Filtrar sessões">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  ref={(el) => {
                    filterRefs.current[f.key] = el;
                  }}
                  type="button"
                  data-ag-filter={f.key}
                  aria-pressed={filter === f.key}
                  onClick={() => setFilter(f.key)}
                >
                  {f.label}
                  {f.key === "saved" && (
                    <>
                      {" "}
                      <span data-saved-count>{savedCount}</span>
                    </>
                  )}
                </button>
              ))}
            </div>
            <label className="ag-search">
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <circle cx="10" cy="10" r="6" />
                <path d="m15 15 6 6" />
              </svg>
              <span className="sr-only">Pesquisar sessões</span>
              <input type="search" placeholder="Procurar sessão…" aria-label="Pesquisar sessões" value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
          </div>

          <p className="ag-results" data-ag-result aria-live="polite">
            {current.label} · {count} {count === 1 ? "sessão" : "sessões"}
          </p>

          <div role="tabpanel" id="ag-panel" aria-labelledby={`ag-tab-${current.key}`}>
            <ul className={`ag-list${cards.some((c) => c.action) ? " ag-list--actions" : ""}`}>
              {cards.map(({ item, action }) => (
                <SessionCard key={item.id} item={item} saved={saved.has(item.id)} action={action} onSave={toggleSaved} />
              ))}
            </ul>
          </div>

          <div className="ag-empty" hidden={count > 0}>
            <h3>A próxima descoberta está noutro filtro.</h3>
            <p>Não há sessões para esta seleção neste dia.</p>
            <button type="button" data-ag-reset onClick={resetFilters}>
              Ver todas as sessões
            </button>
          </div>

          <p className="ag-footnote">Os horários, locais e participantes podem sofrer alterações. Os perfis dos oradores serão publicados após confirmação.</p>
        </div>
      </section>

      <section className="ag-closing" aria-labelledby="ag-closing-title">
        <div className="container">
          <div className="cta">
            <p className="eyebrow">&lt;VEM FAZER PARTE /&gt;</p>
            <h2 id="ag-closing-title">O melhor do ENEI? Estares lá.</h2>
            <p>Já encontraste a tua próxima sessão. Agora vem conhecer as pessoas, partilhar ideias e viver os quatro dias.</p>
            <div className="actions">
              <Link to="/bilhetes" className="btn btn--dark">
                Descobrir os bilhetes
              </Link>
              <Link to="/informacao-ajuda" className="btn btn--secondary">
                Tenho uma dúvida
              </Link>
            </div>
          </div>
        </div>
      </section>

      <div className={`ag-toast${toast ? " is-visible" : ""}`} role="status" aria-live="polite">
        {toast}
      </div>
    </>
  );
}
