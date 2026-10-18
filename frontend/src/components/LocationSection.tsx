import { Link } from 'react-router-dom';
import faroMarinaImg from '../assets/faro-baixa.webp';

export default function LocationSection() {
  return (
    <section className="section home-faro">
      <div className="container split">
        <div className="photo home-faro-photo">
          <img src={faroMarinaImg} alt="Centro histórico de Faro" />
        </div>
        <div>
          <p className="eyebrow">&lt;FARO, ALGARVE /&gt;</p>
          <h2>Uma cidade feita para receber.</h2>
          <p className="lead">
            Faro combina vida académica, acessibilidade, património e a identidade única da Ria
            Formosa.
          </p>
          <div className="actions">
            <Link className="btn btn--secondary" to="/sobre#faro">
              Descobrir Faro
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
