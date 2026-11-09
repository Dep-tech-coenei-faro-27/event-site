import ualg from '../assets/partners/ualg.jpg';
import fct from '../assets/partners/fct.png';
import sas from '../assets/partners/sas.jpg';
import neeec from '../assets/partners/neeec.webp';
import evolution from '../assets/partners/algarve-evolution.png';
import cria from '../assets/partners/ualg-cria.jpg';
import saoBras from '../assets/partners/sao-bras.png';
import tomas from '../assets/partners/tomas-cabreira.png';

/**
 * Os logótipos aparecem nas cores originais, num fundo branco (o fundo branco dos ficheiros some-se nele).
 * `short` é o nome que se vê no cartão (o nome completo fica para os leitores de ecrã). O `crop` (`x y largura altura`) é o `viewBox` que retira só as margens vazias; os ficheiros ficam intactos.
 */
const supporters = [
  { name: 'Universidade do Algarve', src: ualg, width: 738, height: 222, crop: '0 0 738 222' },
  { name: 'Faculdade de Ciências e Tecnologia da Universidade do Algarve', short: 'Faculdade de Ciências e Tecnologia', src: fct, width: 738, height: 357, crop: '80 80 590 220' },
  { name: 'Serviços de Ação Social da Universidade do Algarve', short: 'Serviços de Ação Social', src: sas, width: 374, height: 135, crop: '0 0 374 135' },
  { name: 'NEEEC', src: neeec, width: 1024, height: 1024, crop: '80 80 864 864' },
  { name: 'Algarve Evolution', src: evolution, width: 738, height: 345, crop: '80 75 590 200' },
  { name: 'UAlg Cria', src: cria, width: 586, height: 341, crop: '20 60 550 220' },
  { name: 'Município de São Brás de Alportel', src: saoBras, width: 204, height: 68, crop: '0 0 204 68' },
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
          {supporters.map(({ name, short, src, width, height, crop }) => (
            <li className="partner-card" key={name}>
              <div className="partner-card__logo">
                <svg viewBox={crop} preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">
                  <image href={src} width={width} height={height} />
                </svg>
              </div>
              <p className="partner-card__name">
                {short ? (
                  <>
                    <span aria-hidden="true">{short}</span>
                    <span className="sr-only">{name}</span>
                  </>
                ) : (
                  name
                )}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
