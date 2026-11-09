import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import AgendaVisual from '../components/AgendaVisual';
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

/** A categoria. Os «Guardados» não são uma categoria: são um filtro à parte, que se combina com ela (ex.: palestras guardadas). */
type Filter = "all" | "palestras" | "workshops";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "Tudo" },
  { key: "palestras", label: "Palestras" },
  { key: "workshops", label: "Workshops" },
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

/** Minutos desde a meia-noite do primeiro dia da lista (a discoteca de sexta, às 00:00 de sábado, conta como a seguir ao jantar). */
function minutesIn(starts: string[], start: string): number {
  const stamp = (value: string) => Date.parse(`${value}Z`) / 60000;
  const base = Math.min(...starts.map(stamp));
  const midnight = base - (((base % 1440) + 1440) % 1440);
  return stamp(start) - midnight;
}

/** Hora e posição no ecrã do cartão mais perto do centro, ou nada se o utilizador ainda não chegou à lista. */
function positionToKeep(items: AgendaItem[]): { minutes: number; y: number } | null {
  const middle = window.innerHeight / 2;
  const rects = Array.from(document.querySelectorAll<HTMLElement>(".ag-list > li[data-session]")).flatMap((el) => {
    const start = items.find((i) => i.id === el.dataset.session)?.start;
    return start ? [{ start, rect: el.getBoundingClientRect() }] : [];
  });
  if (rects.length === 0 || rects[0].rect.top > middle) return null; // ainda está acima da lista: nada a manter
  const starts = rects.map((r) => r.start);
  let best = rects[0];
  let bestGap = Infinity;
  for (const entry of rects) {
    const gap = Math.abs(entry.rect.top + entry.rect.height / 2 - middle);
    if (gap < bestGap) {
      best = entry;
      bestGap = gap;
    }
  }
  return { minutes: minutesIn(starts, best.start), y: best.rect.top + best.rect.height / 2 };
}

interface FilterDropdownProps {
  value: Filter;
  onChange: (value: Filter) => void;
}

/**
 * O seletor de categoria dos ecrãs estreitos, feito à mão (o `<select>` nativo usa o aspeto do sistema). É o padrão
 * «combobox só de seleção» do WAI-ARIA: o botão mantém o foco e aponta para a opção ativa com `aria-activedescendant`.
 */
function FilterDropdown({ value, onChange }: FilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const uid = useId();
  const listId = `${uid}-list`;
  const optionId = (index: number) => `${uid}-opt-${index}`;
  const selected = Math.max(0, FILTERS.findIndex((f) => f.key === value));

  useEffect(() => {
    if (!open) return;
    const away = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  const show = () => {
    setActive(selected);
    setOpen(true);
  };
  const choose = (index: number) => {
    onChange(FILTERS[index].key);
    setOpen(false);
  };

  const onKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    const last = FILTERS.length - 1;
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
        event.preventDefault();
        show();
      }
      return;
    }
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        setActive((i) => Math.min(i + 1, last));
        break;
      case "ArrowUp":
        event.preventDefault();
        setActive((i) => Math.max(i - 1, 0));
        break;
      case "Home":
        event.preventDefault();
        setActive(0);
        break;
      case "End":
        event.preventDefault();
        setActive(last);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        choose(active);
        break;
      case "Escape":
        event.preventDefault();
        setOpen(false);
        break;
      case "Tab":
        setOpen(false);
        break;
    }
  };

  return (
    <div ref={root} className={`ag-filter-select${open ? " is-open" : ""}`}>
      <button
        type="button"
        role="combobox"
        className="ag-filter-select__button"
        aria-label="Categoria das sessões"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={open ? optionId(active) : undefined}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={onKey}
      >
        {FILTERS[selected].label}
      </button>
      <ul id={listId} role="listbox" aria-label="Categoria das sessões" className="ag-filter-select__list" hidden={!open}>
        {FILTERS.map((f, index) => (
          <li
            key={f.key}
            id={optionId(index)}
            role="option"
            aria-selected={index === selected}
            className={index === active ? "is-active" : undefined}
            onPointerEnter={() => setActive(index)}
            onPointerDown={(event) => event.preventDefault()}
            onClick={() => choose(index)}
          >
            <span>{f.label}</span>
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="m5 12.5 4.5 4.5L19 7.5" />
            </svg>
          </li>
        ))}
      </ul>
    </div>
  );
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

/** Atividades pagas à parte: levam o aviso de pagamento e o botão de inscrição, ainda indisponível. */
const PAID_ACTIVITY_IDS: ReadonlySet<string> = new Set(['sab-2130-rally-tascas']);

function paidActivityAction(item: AgendaItem): ReactNode {
  return PAID_ACTIVITY_IDS.has(item.id) ? (
    <button type="button" className="ag-action" disabled aria-disabled="true">
      Indisponível
    </button>
  ) : null;
}

function SessionCard({ item, saved, action, onSave }: CardProps) {
  const kind = cardOf(item);
  const end = endOf(item);
  return (
    <li id={item.id} className={`ag-card ag-card--${item.category}${item.tone ? ` ag-card--${item.tone}` : ""}`} data-session={item.id} data-category={item.category}>
      <div className={`ag-card__media${item.image ? ` ag-card__media--activity${item.image.fit === 'cover' ? ' ag-card__media--photo' : ''}` : kind === "speaker" ? "" : " ag-card__media--moment"}`} aria-hidden={kind === "speaker" || item.image ? undefined : true}>
        {item.image ? <img src={item.image.src} alt={item.image.alt} width={168} height={168} loading="lazy" /> : kind === "speaker" ? <Portrait item={item} /> : <AgendaVisual item={item} />}
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
        <div className={`ag-card__foot${PAID_ACTIVITY_IDS.has(item.id) ? " ag-card__foot--paid" : ""}`}>
          <div className="ag-card__foot-info">
            <p className="ag-card__where">
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z" />
                <circle cx="12" cy="10" r="2" />
              </svg>
              {item.location ?? pendingLocation(item)}
            </p>
            {PAID_ACTIVITY_IDS.has(item.id) && <p className="ag-registration-note">Atividade paga · Inscrição obrigatória</p>}
          </div>
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
   * O espaço da ação no canto de cada cartão (inscrição, compra…). Devolve o botão desse item, ou nada. Por omissão só
   * as atividades pagas à parte têm botão (por agora indisponível); o espaço fica reservado para todos terem a mesma altura.
   */
  renderAction?: (item: AgendaItem) => ReactNode;
}

/** A Agenda: proposta B2 (cartões horizontais), escolhida a 26/10/2026. CSS em `agenda.css` e `agenda-base.css`. */
export default function Agenda({ items = AGENDA, renderAction = paidActivityAction }: AgendaProps) {
  useBodyPage("agenda");
  usePageMeta("Agenda · ENEI 2027", "Programa, atividades e experiências do ENEI 2027.");

  const [params, setParams] = useSearchParams();
  const day = dayFromQuery(params.get("dia"));
  const [filter, setFilter] = useState<Filter>("all");
  const [savedOnly, setSavedOnly] = useState(false);
  const [query, setQuery] = useState("");
  const searchInput = useRef<HTMLInputElement>(null);
  const [saved, setSaved] = useState<Set<string>>(() => readSaved(items));
  const [toast, setToast] = useState<string | null>(null);

  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const filterRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const toastTimer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(toastTimer.current), []);

  // O fundo que acompanha os dias (`.ag-days::before/::after`) leva o mesmo azulejo da secção, alinhado com ele. O
  // azulejo da secção desce com a página e os dias ficam presos ao topo, por isso, a cada scroll, diz-se ao CSS onde
  // estão os dias dentro da secção (`--days-x`, `--days-y`).
  const programmeRef = useRef<HTMLElement>(null);
  const daysRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const section = programmeRef.current;
    const days = daysRef.current;
    if (!section || !days) return;
    let frame = 0;
    const update = () => {
      frame = 0;
      const s = section.getBoundingClientRect();
      const d = days.getBoundingClientRect();
      section.style.setProperty("--days-x", `${d.left - s.left}px`);
      section.style.setProperty("--days-y", `${d.top - s.top}px`);
    };
    const schedule = () => {
      if (!frame) frame = window.requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      window.cancelAnimationFrame(frame);
    };
  }, []);

  const pendingScroll = useRef<{ minutes: number; y: number } | null>(null);
  useLayoutEffect(() => {
    const target = pendingScroll.current;
    pendingScroll.current = null;
    if (!target) return;
    const entries = Array.from(document.querySelectorAll<HTMLElement>(".ag-list > li[data-session]")).flatMap((el) => {
      const start = items.find((i) => i.id === el.dataset.session)?.start;
      return start ? [{ el, start }] : [];
    });
    if (entries.length === 0) return;
    const starts = entries.map((e) => e.start);
    let best = entries[0];
    let bestGap = Infinity;
    for (const entry of entries) {
      const gap = Math.abs(minutesIn(starts, entry.start) - target.minutes);
      if (gap < bestGap) {
        best = entry;
        bestGap = gap;
      }
    }
    const rect = best.el.getBoundingClientRect();
    window.scrollBy({ top: rect.top + rect.height / 2 - target.y, behavior: "instant" });
    // `items` não entra: só interessa reagir à troca de dia.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [day]);

  const notify = useCallback((message: string) => {
    window.clearTimeout(toastTimer.current);
    setToast(message);
    toastTimer.current = window.setTimeout(() => setToast(null), 2300);
  }, []);

  // Ao trocar de dia com a lista a meio do ecrã, a lista nova pode ter outro tamanho e deixar o utilizador a olhar para
  // o fim da página. Guarda-se a hora do cartão mais perto do centro do ecrã e onde ele está, e depois da troca leva-se
  // para esse sítio o cartão do dia novo com a hora mais próxima.
  const selectDay = (key: AgendaDay["key"], focus = false) => {
    if (key !== day) pendingScroll.current = positionToKeep(items);
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
    if (wasSaved && savedOnly) window.setTimeout(() => filterRefs.current.saved?.focus(), 0);
  };

  const q = normalize(query.trim());
  const current = AGENDA_DAYS.find((d) => d.key === day) ?? AGENDA_DAYS[1];
  const cards = itemsOfDay(items, current)
    .filter((item) => matchesFilter(item, filter, saved) && (!savedOnly || saved.has(item.id)) && normalize(searchableText(item)).includes(q))
    .map((item) => ({ item, action: renderAction?.(item) ?? null }));
  const count = cards.length;
  const savedCount = items.filter((item) => saved.has(item.id)).length;

  const resetFilters = () => {
    setFilter("all");
    setSavedOnly(false);
    setQuery("");
    filterRefs.current.all?.focus();
  };

  return (
    <>
      <header className="page-hero agenda-hero center">
        <div className="container">
          <p className="eyebrow">&lt;AGENDA /&gt;</p>
          <h1>O programa, dia a dia.</h1>
          <p className="lead">Escolhe o dia. Guarda as sessões a que queres ir.</p>
          <div className="date-pill">1 a 4 de abril de 2027 · Faro</div>
        </div>
      </header>

      <section ref={programmeRef} className="ag-programme" id="programa" aria-label="Programa por dia">
        <div className="container">
          <h2 className="sr-only">Sessões por dia</h2>

          <div ref={daysRef} role="tablist" aria-label="Dias do programa" className="ag-days">
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
                </button>
              ))}
            </div>
            {/* Em ecrãs estreitos (CSS) as pílulas das categorias dão lugar a este seletor, para a pesquisa ficar na mesma fila. */}
            <FilterDropdown value={filter} onChange={setFilter} />
            {/* Os «Guardados» combinam com a categoria (palestras guardadas…). Em ecrãs estreitos só se vê o ícone e o número. */}
            <button
              ref={(el) => {
                filterRefs.current.saved = el;
              }}
              type="button"
              className="ag-saved-pill"
              data-ag-filter="saved"
              aria-pressed={savedOnly}
              onClick={() => setSavedOnly((on) => !on)}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M6 4h12v17l-6-4-6 4Z" />
              </svg>
              <span className="ag-saved-pill__label">Guardados</span>{" "}
              <span data-saved-count>{savedCount}</span>
            </button>
            <div className="ag-search">
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <circle cx="10" cy="10" r="6" />
                <path d="m15 15 6 6" />
              </svg>
              <input ref={searchInput} type="search" placeholder="Procurar sessão…" aria-label="Pesquisar sessões" value={query} onChange={(event) => setQuery(event.target.value)} />
              {query !== "" && (
                <button
                  type="button"
                  className="ag-search__clear"
                  aria-label="Limpar pesquisa"
                  onClick={() => {
                    setQuery("");
                    searchInput.current?.focus();
                  }}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M6 6l12 12M18 6L6 18" />
                  </svg>
                </button>
              )}
            </div>
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
            <h3>Sem sessões nesta seleção.</h3>
            <p>Não há sessões para esta seleção neste dia.</p>
            <button type="button" data-ag-reset onClick={resetFilters}>
              Ver todas as sessões
            </button>
          </div>

          <p className="ag-footnote">Programa sujeito a alterações. Locais e oradores por confirmar.</p>
          <p className="ag-registration-note">Guardar uma sessão não garante lugar. <Link to="/informacao-ajuda">Consulta as condições de inscrição.</Link></p>
        </div>
      </section>

      <section className="ag-closing" aria-labelledby="ag-closing-title">
        <div className="container">
          <div className="cta">
            <p className="eyebrow">&lt;VEM FAZER PARTE /&gt;</p>
            <h2 id="ag-closing-title">O melhor do ENEI? Estares lá.</h2>
            <p>Escolhe o teu bilhete e junta-te a nós em Faro.</p>
            <div className="actions">
              <Link to="/bilhetes" className="btn btn--dark">
                Ver bilhetes
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
