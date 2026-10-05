import Navbar from "../components/Navbar";
import TeamHero from "../components/equipa/TeamHero";
import TeamIntro from "../components/equipa/TeamIntro";
import TeamDepartment from "../components/equipa/TeamDepartment";
import TeamCta from "../components/equipa/TeamCta";
import { departments } from "../data/Team";

export default function Equipa() {
  return (
    <>
      <Navbar />
      <main id="conteudo" className="p-t-16">
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