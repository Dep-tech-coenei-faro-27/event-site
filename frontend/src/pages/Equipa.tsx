import TeamHero from "../components/equipa/TeamHero";
import TeamIntro from "../components/equipa/TeamIntro";
import TeamDepartment from "../components/equipa/TeamDepartment";
import TeamCta from "../components/equipa/TeamCta";
import { departments } from "../data/Team";
import { usePageMeta } from "../utils/usePageMeta";


export default function Equipa() {

    usePageMeta("Equipa · ENEI 2027", "As pessoas por trás do ENEI 2027.");

  return (
    <>
      <main id="conteudo" className="pt-16">
        <TeamHero />

        <TeamIntro/>

        {departments.map((d, i) => (
          <TeamDepartment key={d.id} {...d} alternate={i % 2 === 1} />
        ))}

        <TeamCta />
      </main>
    </>
  );
}