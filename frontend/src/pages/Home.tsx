import AboutSection from '../components/AboutSection';
import Hero from '../components/Hero';
import ParticipationSection from '../components/ParticipationSection';
import ProgramSection from '../components/ProgramSection';
import QuickInfo from '../components/QuickInfo';
import LocationSection from '../components/LocationSection'
import ExperienceSection from '../components/ExperienceSection';
import PartnersSection from '../components/PartnersSection';
import CtaBanner from '../components/CtaBanner';
import { usePageMeta } from "../utils/usePageMeta";
import { useBodyPage } from "../utils/useBodyPage";

// As secções são filhas diretas do `<main>` (o do App): o CSS do desenho novo conta-as por
// ordem (`main > .section:nth-of-type(odd)`), por isso não há um contentor entre elas.
function Home() {
    usePageMeta("ENEI 2027", "Encontro Nacional de Estudantes de Informática.");
    useBodyPage("inicio");

    return (
        <>
            <Hero />
            <QuickInfo />
            <AboutSection />
            <ParticipationSection />
            <ProgramSection />
            <LocationSection />
            <ExperienceSection />
            <PartnersSection />
            <CtaBanner />
        </>
    )
}

export default Home;
