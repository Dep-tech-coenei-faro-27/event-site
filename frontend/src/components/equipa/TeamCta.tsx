const button =
  "inline-flex items-center rounded-full px-6 py-3 font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white";

export default function TeamCta() {
  return (
    <section className=" bg-azul-base py-16 md:py-20">
      <div className="mx-auto w-full max-w-6xl px-6">
        <div className="azulejo-bg [--azulejo-opacity:0.25] rounded-3xl bg-gradient-to-br from-ciano-profundo to-ciano-digital p-10 text-white md:p-16">
          <p className="font-mono text-sm font-medium">{"<COMUNIDADE />"}</p>
          <h2 className="mt-3 max-w-2xl text-3xl font-bold md:text-4xl">
            Uma equipa aberta ao ecossistema.
          </h2>
          <p className="mt-4 max-w-xl text-white/90">
            A organização trabalha com a Universidade do Algarve, associações
            académicas, entidades públicas, comunidades e empresas.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="mailto:equipa@enei.pt" className={`${button} bg-azul-base hover:bg-azul-superficie`}>
              Contactar a equipa
            </a>
            <a href="/parcerias" className={`${button} bg-white/15 hover:bg-white/25`}>
              Conhecer parcerias
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}