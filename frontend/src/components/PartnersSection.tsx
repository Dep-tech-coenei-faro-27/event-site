import { useEffect, useRef } from 'react';
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

/** Remove the light matte and render the previous inverted greyscale treatment. */
function PartnerLogo({ name, src, crop }: { name: string; src: string; crop: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [x, y, width, height] = crop.split(' ').map(Number);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return;
    const image = new Image();
    image.onload = () => {
      context.clearRect(0, 0, width, height);
      context.drawImage(image, x, y, width, height, 0, 0, width, height);
      const pixels = context.getImageData(0, 0, width, height);
      const data = pixels.data;
      const shades = new Uint8Array(width * height);
      for (let pixel = 0; pixel < shades.length; pixel++) {
        const p = pixel * 4;
        const luminance = 0.2126 * data[p] + 0.7152 * data[p + 1] + 0.0722 * data[p + 2];
        shades[pixel] = 255 - Math.min(255, Math.max(0, (luminance - 127.5) * 1.4 + 127.5));
      }
      const background = new Uint8Array(width * height);
      const queue = new Int32Array(width * height);
      let head = 0;
      let tail = 0;
      const visit = (pixel: number) => {
        if (background[pixel]) return;
        const p = pixel * 4;
        const low = Math.min(data[p], data[p + 1], data[p + 2]);
        const high = Math.max(data[p], data[p + 1], data[p + 2]);
        if (data[p + 3] === 0 || (low >= 225 && high - low <= 25)) {
          background[pixel] = 1;
          queue[tail++] = pixel;
        }
      };
      for (let column = 0; column < width; column++) {
        visit(column);
        visit((height - 1) * width + column);
      }
      for (let row = 0; row < height; row++) {
        visit(row * width);
        visit(row * width + width - 1);
      }
      while (head < tail) {
        const pixel = queue[head++];
        if (pixel % width > 0) visit(pixel - 1);
        if (pixel % width < width - 1) visit(pixel + 1);
        if (pixel >= width) visit(pixel - width);
        if (pixel < width * (height - 1)) visit(pixel + width);
      }
      for (let pixel = 0; pixel < background.length; pixel++) visit(pixel);
      for (let pixel = 0; pixel < background.length; pixel++) {
        const p = pixel * 4;
        if (background[pixel]) {
          data[p + 3] = 0;
          continue;
        }
        const column = pixel % width;
        const touchesBackground = (column > 0 && background[pixel - 1])
          || (column < width - 1 && background[pixel + 1])
          || (pixel >= width && background[pixel - width])
          || (pixel < width * (height - 1) && background[pixel + width]);
        if (!touchesBackground) continue;
        const alpha = 1 - Math.min(data[p], data[p + 1], data[p + 2]) / 255;
        if (alpha <= 0) { data[p + 3] = 0; continue; }
        for (let channel = 0; channel < 3; channel++) {
          data[p + channel] = Math.max(0, (data[p + channel] - 255 * (1 - alpha)) / alpha);
        }
        data[p + 3] = Math.round(data[p + 3] * alpha);
      }
      for (let pixel = 0; pixel < shades.length; pixel++) {
        const p = pixel * 4;
        data[p] = data[p + 1] = data[p + 2] = shades[pixel];
      }
      context.putImageData(pixels, 0, 0);
    };
    image.src = src;
    return () => { image.onload = null; };
  }, [name, src, x, y, width, height]);

  return <canvas ref={ref} width={width} height={height} role="img" aria-label={name}>{name}</canvas>;
}
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
          {supporters.map(({ name, src, crop }) => (
            <li key={name}>
              <PartnerLogo name={name} src={src} crop={crop} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
