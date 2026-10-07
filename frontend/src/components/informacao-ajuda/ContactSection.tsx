import Eyebrow from "../EyeBrow";
import PrimaryButton from "../PrimaryButton";
import SecondaryButton from "../SecundaryButton";

export default function ContactSection() {
  return (
    <section className="azulejo-bg bg-[#081126] py-[clamp(72px,9vw,124px)]">
      <div className="mx-auto grid w-[min(calc(100%-28px),1180px)] items-center gap-10 sm:w-[min(calc(100%-40px),1180px)] md:grid-cols-2 md:gap-24">
        <div>
            <Eyebrow text="CONTACTO"/>
          <h2 className="text-[clamp(30px,4vw,52px)] font-semibold leading-[1.06] tracking-[-0.045em] text-white">
            Ainda tens dúvidas?
          </h2>
          <p className="mt-5 max-w-[720px] text-[clamp(17px,2vw,20px)] text-[#b1bccd]">
            A nossa equipa ajuda-te a encontrar a informação certa.
          </p>
            <div className="mt-7 flex flex-wrap items-center justify-center gap-4">
                <a href="mailto:geral@enei.pt">
                    <SecondaryButton text="Enviar Email" />
                </a>
                <PrimaryButton text="Contactar" />
            </div>
        </div>

        <aside className="border-y border-[#1ab2ff]/40 bg-gradient-to-r from-[#1ab2ff]/10 to-transparent p-7">
          <h3 className="text-xl font-semibold tracking-tight text-white">Canais de apoio</h3>
          <ul className="mt-5 grid gap-2.5 text-[#b1bccd]">
            {['geral@enei.pt', 'Faro, Algarve', 'Resposta em horário útil'].map((t) => (
              <li key={t} className="flex items-center gap-3">
                <svg viewBox="0 0 24 24" aria-hidden="true" className="h-[17px] w-[17px] shrink-0 fill-none stroke-[#1ab2ff] stroke-[2.25]" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m5 12 4 4L19 6" />
                </svg>
                {t}
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </section>
  );
}