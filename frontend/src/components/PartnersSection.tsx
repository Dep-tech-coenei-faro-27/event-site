import ualg from '../assets/partners/ualg.jpg';
import fct from '../assets/partners/fct.png';
import sas from '../assets/partners/sas.jpg';
import neeec from '../assets/partners/neeec.webp';
import evolution from '../assets/partners/algarve-evolution.png';
import cria from '../assets/partners/ualg-cria.jpg';
import saoBras from '../assets/partners/sao-bras.jpg';
import tomas from '../assets/partners/tomas-cabreira.png';

/** O viewBox retira só as margens vazias; os ficheiros originais ficam intactos. */
const supporters = [
  { name: 'Universidade do Algarve', src: ualg, width: 738, height: 222, crop: '0 0 738 222' },
  { name: 'Faculdade de Ciências e Tecnologia da Universidade do Algarve', src: fct, width: 738, height: 357, crop: '80 80 590 220' },
  { name: 'Serviços de Ação Social da Universidade do Algarve', src: sas, width: 374, height: 135, crop: '0 0 374 135' },
  { name: 'NEEEC', src: neeec, width: 1024, height: 1024, crop: '80 80 864 864' },
  { name: 'Algarve Evolution', src: evolution, width: 738, height: 345, crop: '80 75 590 200' },
  { name: 'UAlg Cria', src: cria, width: 586, height: 341, crop: '20 60 550 220' },
  { name: 'Município de São Brás de Alportel', src: saoBras, width: 1000, height: 667, crop: '350 180 300 300' },
  { name: 'Agrupamento de Escolas Tomás Cabreira', src: tomas, width: 738, height: 369, crop: '0 0 738 369' },
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
          {supporters.map(({ name, src, width, height, crop }) => (
            <li key={name}>
              <svg viewBox={crop} role="img" aria-label={name}>
                <title>{name}</title>
                <image href={src} width={width} height={height} />
              </svg>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
