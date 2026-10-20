import "../equipa.css";
import TeamCta from "../components/equipa/TeamCta";
import TeamDepartment from "../components/equipa/TeamDepartment";
import TeamHero from "../components/equipa/TeamHero";
import TeamIntro from "../components/equipa/TeamIntro";
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
      <TeamIntro />
      {departments.map((department) => (
        <TeamDepartment key={department.id} {...department} />
      ))}
      <TeamCta />
    </>
  );
}
