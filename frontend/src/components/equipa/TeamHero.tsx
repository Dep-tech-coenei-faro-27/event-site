/** Cabeçalho da página Equipa (`ui-ux/equipa`): a fotografia da equipa vem do CSS (`equipa.css`). */
export default function TeamHero() {
  return (
    <header className="page-hero team-hero">
      <div className="container">
        <div className="team-hero__copy">
          <p className="eyebrow">&lt;EQUIPA /&gt;</p>
          <h1>As pessoas por trás<br />{' '}do ENEI 2027.</h1>
          <p className="lead">Estudantes a preparar os teus quatro dias em Faro.</p>
        </div>
      </div>
    </header>
  );
}
