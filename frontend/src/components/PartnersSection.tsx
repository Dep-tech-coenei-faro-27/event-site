/** Parceiros e apoios na página inicial (substitui a página Parcerias, que deixou de existir). */
const supporters = [
  'UAlg',
  'FCT UAlg',
  'SAS UAlg',
  'NEEC',
  'Algarve Evolution',
  'UAlg Cria',
  'CM São Brás',
  'Tomás Cabreira',
];

export default function PartnersSection() {
  return (
    <section className="section section--surface home-partners" id="parceiros">
      <div className="container">
        <div className="section-heading">
          <div>
            <p className="eyebrow">&lt;PARCEIROS /&gt;</p>
            <h2>Quem apoia o ENEI.</h2>
          </div>
          <p className="lead">Instituições académicas, autarquias e organizações tecnológicas unidas à comunidade ENEI.</p>
        </div>
        <ul className="home-partners__grid" aria-label="Parceiros e apoios">
          {supporters.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
