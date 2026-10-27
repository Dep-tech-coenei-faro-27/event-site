import "../equipa.css";
import "../equipa.overrides.css";
import TeamDepartment from "../components/equipa/TeamDepartment";
import TeamHero from "../components/equipa/TeamHero";
import { departments } from "../data/Team";
import { useBodyPage } from "../utils/useBodyPage";
import { usePageMeta } from "../utils/usePageMeta";

/** `ui-ux/equipa`. As pessoas vêm de `data/Team.ts`; o aspeto vem do CSS gerado do protótipo (`equipa.css`). */
export default function Equipa() {
  useBodyPage("equipa");
  usePageMeta("Equipa · ENEI 2027", "As pessoas por trás do ENEI 2027.");

  return (
    <>
      <TeamHero />
      {departments.map((department) => (
        <TeamDepartment key={department.id} {...department} />
      ))}
    </>
  );
}
