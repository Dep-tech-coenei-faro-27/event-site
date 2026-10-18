const details = [
  { label: 'Recinto', text: 'Atividades principais no Campus das Gambelas.' },
  { label: 'Alimentação', text: 'Refeições servidas na cantina do campus.' },
  { label: 'Alojamento', text: 'Alojamento coletivo para participantes.' },
  { label: 'Mobilidade', text: 'Rede dedicada de transporte entre pontos do evento.' },
];

export default function ExperienceSection() {
  return (
    <section className="section section--panel home-experience">
      <div className="container">
        <p className="eyebrow">&lt;EXPERIÊNCIA /&gt;</p>
        <blockquote className="editorial-quote">
          Um encontro que combina aprendizagem, competição, cultura académica algarvia e uma
          plataforma de gamificação para manter toda a comunidade ligada.
          <cite>Visão ENEI Faro 2027</cite>
        </blockquote>
        <div className="ops-strip" style={{ marginTop: 34 }}>
          {details.map((item) => (
            <div className="ops-item" key={item.label}>
              <small>{item.label}</small>
              <p>{item.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
