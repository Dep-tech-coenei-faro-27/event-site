import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import BrandLogo from './BrandLogo';
import logoNeei from '../assets/neei-logo.webp';
import { EVENT_DATES } from '../data/Event';

interface SocialLink {
  label: string;
  href: string;
  icon: ReactNode;
}

const socials: SocialLink[] = [
  {
    label: 'Instagram',
    href: 'https://www.instagram.com/eneiconf/',
    icon: (
      <>
        <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
        <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
        <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
      </>
    ),
  },
  {
    label: 'Facebook',
    href: 'https://www.facebook.com/eneiconf/?locale=pt_PT',
    icon: <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />,
  },
  {
    label: 'LinkedIn',
    href: 'https://pt.linkedin.com/company/eneiconf',
    icon: (
      <>
        <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
        <rect x="2" y="9" width="4" height="12" />
        <circle cx="4" cy="4" r="2" />
      </>
    ),
  },
];

// Três colunas a partir dos 901px, com colunas flexíveis para não comprimir as ligações.
// Medidas do rodapé do desenho novo (`ui-ux/src/core.css`, `.site-footer`): títulos e listas a 14px,
// 9px entre ligações, etiquetas a 10px, linhas com a cor `--line`.
const LINE = 'border-[rgba(215,227,244,0.1)]';
const headingClass = 'm-0 mb-4 text-[14px] font-bold leading-[1.06] tracking-[-0.045em] text-branco';
const listClass = 'm-0 grid list-none gap-[9px] p-0 text-[14px] leading-[1.65]';
const labelClass =
  'mb-[13px] block font-montserrat text-[10px] font-bold uppercase leading-none tracking-[0.14em] text-cinza-subtil';

export default function Footer() {
  return (
    <>
    <footer className={`site-footer border-t ${LINE} bg-azul-noite pb-6 pt-12 font-poppins text-cinza-texto`}>
      <div className="mx-auto w-[calc(100%-40px)] max-w-[1180px] min-[901px]:w-[calc(100%-80px)]">
        {/* Três blocos: identidade, ligações (Explorar e Participar) e organização e redes */}
        <div className="footer-main grid grid-cols-1 items-start gap-8 min-[621px]:grid-cols-2 min-[901px]:gap-8 min-[901px]:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_auto]">
          {/* Identidade */}
          <div className="footer-identity flex flex-col min-[621px]:col-span-2 min-[901px]:col-span-1">
            <BrandLogo
              className="gap-4 text-[27px] md:text-[30px]"
              imageClassName="h-[55px] w-[44px] md:h-[60px] md:w-[48px]"
            />
            <p className="m-0 mt-5 max-w-[410px] text-[15px] leading-[1.65] min-[621px]:max-[900px]:max-w-none">
              Encontro Nacional de Estudantes de Informática · Faro, Algarve · {EVENT_DATES}.
            </p>
          </div>

          {/* Explorar e Participar */}
          <div className="footer-navigation grid grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] gap-6">
            <div>
              <h2 className={headingClass}>Explorar</h2>
              <ul className={listClass}>
                <li><Link to="/sobre" className="transition-colors hover:text-branco">Sobre</Link></li>
                <li><Link to="/agenda" className="transition-colors hover:text-branco">Agenda</Link></li>
                <li><Link to="/#parceiros" className="transition-colors hover:text-branco">Parceiros</Link></li>
              </ul>
            </div>
            <div>
              <h2 className={headingClass}>Participar</h2>
              <ul className={listClass}>
                <li><Link to="/conta" className="transition-colors hover:text-branco">Entrar</Link></li>
                <li><Link to="/bilhetes" className="transition-colors hover:text-branco">Bilhetes</Link></li>
                <li><Link to="/informacao-ajuda" className="transition-colors hover:text-branco">Informações e ajuda</Link></li>
              </ul>
            </div>
          </div>

          {/* Organizado por + redes sociais */}
          <div className={`footer-connect flex flex-wrap items-start justify-between gap-6 border-t ${LINE} pt-6 min-[621px]:grid min-[621px]:grid-cols-1 min-[621px]:gap-6 min-[621px]:border-t-0 min-[621px]:pt-0 min-[621px]:border-l min-[621px]:pl-6 min-[621px]:max-[900px]:justify-self-end`}>
            <div className="w-fit">
              <span className={labelClass}>Organizado por</span>
              <img
                src={logoNeei}
                alt="NEEI — Núcleo de Estudantes de Engenharia Informática"
                className="h-auto w-[78px] object-contain min-[621px]:w-[88px]"
              />
            </div>

            <div className="w-fit">
              <span className={labelClass}>Segue o ENEI</span>
              <div className="flex gap-[7px]">
                {socials.map(({ label, href, icon }) => (
                  <a
                    key={label}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${label} (abre noutro separador)`}
                    className={`flex h-[42px] w-[42px] items-center justify-center rounded-[2px] border ${LINE} bg-transparent transition-all hover:border-branco/30 hover:bg-branco/5 hover:text-branco`}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                      className="h-4 w-4 fill-none stroke-current stroke-[1.7]"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      {icon}
                    </svg>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Barra inferior */}
        <div className={`mt-8 flex flex-col items-start justify-between gap-6 border-t ${LINE} pt-5 text-[12px] text-cinza-subtil min-[901px]:flex-row min-[901px]:items-center`}>
          <p className="m-0">© 2027 ENEI. Todos os direitos reservados.</p>
          <div className="flex flex-wrap justify-start gap-3 min-[621px]:justify-end min-[621px]:gap-[18px]">
            <Link to="/termos" className="transition-colors hover:text-branco">Termos e condições</Link>
            <Link to="/privacidade" className="transition-colors hover:text-branco">Política de privacidade</Link>
            <Link to="/acessibilidade" className="transition-colors hover:text-branco">Declaração de Acessibilidade</Link>
          </div>
        </div>
      </div>
    </footer>
    </>
  );
}
