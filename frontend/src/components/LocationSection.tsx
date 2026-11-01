import { Link } from 'react-router-dom';
import campus from '../assets/campus-gambelas-ualg.webp';

export default function LocationSection() {
  return (
    <section className="section home-practical">
      <div className="container split">
        <figure className="preview-photo">
          <img src={campus} alt="Edifício 1 do Campus das Gambelas, com a entrada e a fachada de arcos" width={1600} height={1066} loading="lazy" />
          <figcaption><span>O ponto de encontro</span><small>Fotografia: UAlg</small></figcaption>
        </figure>
        <div>
          <p className="eyebrow">Prepara a viagem</p>
          <h2>Próxima paragem: Faro.</h2>
          <p className="home-practical__intro">O ENEI chega a sul. Quatro dias para trocar ideias, conhecer a tua malta e viver a cidade.</p>
          <dl className="home-practical__facts">
            <div><dt>Onde</dt><dd>Campus das Gambelas, Universidade do Algarve.</dd></div>
            <div><dt>Estadia</dt><dd>Alojamento coletivo incluído no bilhete Experiência completa.</dd></div>
            <div><dt>Refeições</dt><dd>Servidas na cantina do campus.</dd></div>
          </dl>
          <div className="actions"><Link className="btn btn--secondary" to="/informacao-ajuda#localizacoes">Ver locais e acessos</Link></div>
        </div>
      </div>
    </section>
  );
}
