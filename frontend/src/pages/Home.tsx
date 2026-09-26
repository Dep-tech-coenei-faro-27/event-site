import ContactSupportForm from "../components/ContactSupportForm";
import FaqSection from "../components/FaqSection";

function Home() {
    return (
        <div className="p-12">
            <h1 className="text-3xl font-bold">Pagina inicial </h1>
            <p> Bem-vindo ao ENEI!</p>
            <FaqSection />
            <ContactSupportForm />
        </div>
    )
}

export default Home;