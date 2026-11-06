import ualg from '../assets/partners/ualg-white.svg';
import fct from '../assets/partners/fct-white.svg';
import sas from '../assets/partners/sas-white.svg';
import neeec from '../assets/partners/neeec-white.svg';
import evolution from '../assets/partners/algarve-evolution-white.svg';
import cria from '../assets/partners/ualg-cria-white.svg';
import saoBras from '../assets/partners/sao-bras-white.svg';
import tomas from '../assets/partners/tomas-cabreira-white.svg';

const supporters = [
  { name: 'Universidade do Algarve', src: ualg },
  { name: 'Faculdade de Ciências e Tecnologia da Universidade do Algarve', src: fct },
  { name: 'Serviços de Ação Social da Universidade do Algarve', src: sas },
  { name: 'NEEEC', src: neeec },
  { name: 'Algarve Evolution', src: evolution },
  { name: 'UAlg Cria', src: cria },
  { name: 'Município de São Brás de Alportel', src: saoBras },
  { name: 'Agrupamento de Escolas Tomás Cabreira', src: tomas },
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
        </div>
        <ul className="home-partners__grid" aria-label="Parceiros e apoios">
          {supporters.map(({ name, src }) => (
            <li key={name}>
              <img src={src} alt={name} width={738} height={240} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}