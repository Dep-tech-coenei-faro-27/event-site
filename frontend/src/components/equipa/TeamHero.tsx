/** Cabeçalho da página Equipa (`ui-ux/equipa`): a fotografia da equipa vem do CSS (`equipa.css`). */
export default function TeamHero() {
  return (
    <header className="page-hero team-hero">
      <div className="container">
        <p className="sr-only">Fotografia da equipa organizadora do ENEI 2027 reunida na praia.</p>
        <p className="eyebrow">&lt;EQUIPA /&gt;</p>
        <h1>As pessoas por trás do ENEI 2027.</h1>
        <p className="lead">
          Uma estrutura organizada por áreas de especialidade para transformar ambição estudantil numa experiência nacional.
        </p>
      </div>
    </header>
  );
}
