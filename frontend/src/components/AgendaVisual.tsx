import type { AgendaItem } from '../content/agenda';

/** Pictogramas com o mesmo traço, sem decoração, para identificar cada atividade. */
export default function AgendaVisual({ item }: { item: AgendaItem }) {
  const title = item.title.toLocaleLowerCase('pt-PT');
  const symbol = title.includes('prémios') ? 'trophy'
    : item.kind === 'Refeição' ? 'meal'
    : title.includes('banho') ? 'shower'
    : title.includes('pistas') || title.includes('peddy') ? 'route'
    : title.includes('tascas') ? 'toast'
    : title.includes('boas-vindas') ? 'welcome'
    : title.includes('arraial') || title.includes('discoteca') ? 'music'
    : item.kind === 'Tertúlia' ? 'discussion'
    : item.category === 'palestras' ? 'talk'
    : 'activity';

  const drawings = {
    trophy: <><path d="M7 3h10v5a5 5 0 0 1-10 0V3ZM7 5H4v2a4 4 0 0 0 4 4m9-6h3v2a4 4 0 0 1-4 4M12 13v5m-4 3v-3h8v3H8Z" /></>,
    meal: <><path d="M5 3v6m3-6v6M2 3v6a3 3 0 0 0 6 0m-3 3v9M19 21V3c-4 2-5 6-5 10h5" /></>,
    shower: <><path d="M5 21V7a4 4 0 0 1 8 0v1m-4 4a4 4 0 0 1 8 0H9Zm1 4v1m3-1v1m3-1v1m-7 3v1m4-1v1m4-1v1" /></>,
    route: <><circle cx="5" cy="5" r="2" /><circle cx="19" cy="19" r="2" /><path d="M7 5h9a4 4 0 0 1 0 8H8a3 3 0 0 0 0 6h9" /></>,
    toast: <><path d="m4 3 6 2-2 7a3 3 0 0 1-5-2l1-7Zm16 0-6 2 2 7a3 3 0 0 0 5-2l-1-7ZM5 13l-2 7m-2-1 5 2m13-8 2 7m-3 1 5-2M11 2l1 2 1-2" /></>,
    welcome: <><path d="M4 21h16M6 21V3h12v18M9 12h6m-3-3 3 3-3 3" /></>,
    music: <><path d="M9 18V5l11-2v13M9 8l11-2" /><ellipse cx="6" cy="18" rx="3" ry="2.5" /><ellipse cx="17" cy="16" rx="3" ry="2.5" /></>,
    discussion: <><path d="M14 14H8l-4 3V4h14v6m-6 4v4h4l4 3V10h-2M8 8h6" /></>,
    talk: <><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4m-4 0h8" /></>,
    activity: <><rect x="3" y="4" width="18" height="13" rx="1" /><path d="M1 21h22m-14-13-3 3 3 3m6-6 3 3-3 3" /></>,
  };

  return <div className="ag-visual" data-symbol={symbol} aria-hidden="true">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" focusable="false">
      {drawings[symbol]}
    </svg>
  </div>;
}
