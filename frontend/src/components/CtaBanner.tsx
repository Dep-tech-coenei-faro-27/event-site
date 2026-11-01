import { Link } from 'react-router-dom';
import eneiLogo from '../assets/ENEI-logo.svg';

export default function CtaBanner() {
  return (
    <section className="section section--surface home-closing">
      <div className="container">
        <div className="cta azulejo-bg">
          <div className="home-closing__passer" aria-hidden="true">
            <img src={eneiLogo} alt="" />
          </div>
          <p className="eyebrow" style={{ color: 'white' }}>
            &lt;ENEI_2027 /&gt;
          </p>
          <h2>Falta só estares lá.</h2>
          <p className="home-closing__lead">Traz a curiosidade. Leva novas ideias, novas amizades e quatro dias para recordar.</p>
          <div className="actions">
            <Link className="btn btn--dark" to="/bilhetes">
              Comprar bilhete
            </Link>
            <Link className="btn btn--outline-light" to="/informacao-ajuda">
              Tenho dúvidas
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
