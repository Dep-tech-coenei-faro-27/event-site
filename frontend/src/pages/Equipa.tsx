import "../equipa.css";
import "../equipa.overrides.css";
import TeamDepartment from "../components/equipa/TeamDepartment";
import TeamHero from "../components/equipa/TeamHero";
import { departments } from "../data/Team";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";
import { useRef, useState } from 'react';

/** `ui-ux/equipa`. As pessoas vêm de `data/Team.ts`; o aspeto vem do CSS gerado do protótipo (`equipa.css`). */
export default function Equipa() {
  useBodyPage("equipa");
  usePageMeta("Equipa · ENEI 2027", "As pessoas por trás do ENEI 2027.");
  const [selected, setSelected] = useState('all');
  const [filterOpen, setFilterOpen] = useState(false);
  const filterTrigger = useRef<HTMLButtonElement>(null);
  const options = [
    { id: 'all', label: 'Tudo', count: departments.reduce((total, department) => total + department.members.length, 0) },
    ...departments.map(({ id, label, members }) => ({ id, label, count: members.length })),
  ];
  const visibleDepartments = selected === 'all' ? departments : departments.filter(({ id }) => id === selected);
  const currentOption = options.find(({ id }) => id === selected)!;

  return (
    <>
      <TeamHero />
      <div className="departments-nav container" role="group" aria-label="Filtrar departamentos">
        <div className="departments-nav__links">
          {options.map(({ id, label, count }) => (
            <button key={id} type="button" onClick={() => setSelected(id)} aria-pressed={selected === id}>
              <span className="departments-nav__label">{label}</span>
              <span className="departments-nav__count" aria-label={`${count} pessoas`}>{String(count).padStart(2, '0')}</span>
            </button>
          ))}
        </div>
        <div className="departments-nav__select" onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setFilterOpen(false);
            filterTrigger.current?.focus();
          }
        }}>
          <span id="department-filter-label">Departamento</span>
          <button ref={filterTrigger} type="button" className="departments-nav__trigger" aria-labelledby="department-filter-label department-filter-value" aria-expanded={filterOpen} aria-controls="department-filter-options" onClick={() => setFilterOpen(!filterOpen)}>
            <span id="department-filter-value">{currentOption.label}</span>
            <span className="departments-nav__total">{currentOption.count} pessoas</span>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m5 8 5 5 5-5" /></svg>
          </button>
          <div id="department-filter-options" className="departments-nav__options" hidden={!filterOpen} role="group" aria-label="Escolher departamento">
            {options.map(({ id, label, count }) => (
              <button key={id} type="button" aria-pressed={selected === id} onClick={() => {
                setSelected(id);
                setFilterOpen(false);
                filterTrigger.current?.focus();
              }}>
                <span>{label}</span><span className="departments-nav__count">{count}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
      <p className="sr-only" role="status">
        {selected === 'all' ? 'A mostrar todos os departamentos.' : `A mostrar apenas ${options.find(({ id }) => id === selected)?.label}.`}
      </p>
      {visibleDepartments.map((department) => (
        <TeamDepartment key={department.id} {...department} />
      ))}
    </>
  );
}
