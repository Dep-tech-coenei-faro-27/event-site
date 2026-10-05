import Eyebrow from "../EyeBrow";


export default function TeamIntro() {
  return (
    <section className="azulejo-bg bg-[#050d21] py-16 md:py-24">
      <div className="mx-auto grid w-full max-w-6xl items-center gap-8 px-6 md:grid-cols-2 md:gap-12">
        <div>
          <Eyebrow text={"EQUIPA COMPLETA"} />
          <h2 className="mt-2 text-3xl font-bold text-branco md:text-4xl">Pessoas diferentes.<br></br> O mesmo espaço.</h2>
        </div>
        <p className="text-lg text-cinza-texto">A equipa está organizada por departamentos, com o mesmo formato e a mesma dimensão para todas as pessoas.</p>
      </div>
    </section>
  );
}