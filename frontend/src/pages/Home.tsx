
import AboutSection from '../components/AboutSection';
import Hero from '../components/Hero';
import ParticipationSection from '../components/ParticipationSection';
import ProgramSection from '../components/ProgramSection';
import QuickInfo from '../components/QuickInfo';
import LocationSection from '../components/LocationSection'
import ExperienceSection from '../components/ExperienceSection';
import CtaBanner from '../components/CtaBanner';
import { usePageMeta } from "../utils/usePageMeta";

function Home() {
    
    usePageMeta("ENEI 2027", "Encontro Nacional de Estudantes de Informática.");

    return (
        <>
            <main className="min-h-screen bg-[#050d21] overflow-x-hidden selection:bg-[#00AAFF]/30 pt-16">
                <Hero />

                <QuickInfo />
                <AboutSection />
                <ParticipationSection />
                <ProgramSection />
                <LocationSection />
                <ExperienceSection />
                <CtaBanner />
            </main>
        </>
    )
}

export default Home;
