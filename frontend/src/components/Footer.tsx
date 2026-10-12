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
    href: '#',
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
    href: '#',
    icon: <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />,
  },
  {
    label: 'LinkedIn',
    href: '#',
    icon: (
      <>
        <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
        <rect x="2" y="9" width="4" height="12" />
        <circle cx="4" cy="4" r="2" />
      </>
    ),
  },
];

// Títulos e listas: 14px / 1.06 e links com gap de 9px no mobile (como no styles.css original)
const headingClass =
  'm-0 mb-4 text-[14px] font-bold leading-[1.06] text-branco md:mb-5 md:text-[15px] md:leading-normal';
const listClass =
  'm-0 flex list-none flex-col gap-[9px] p-0 text-[14px] leading-[1.65] md:gap-2.5 md:leading-normal';
const labelClass =
  'mb-3 block font-montserrat text-[10px] font-bold uppercase tracking-[0.16em] text-cinza-subtil';

export default function Footer() {
  return (
    <footer className="border-t border-branco/5 bg-azul-noite pb-6 pt-16 font-poppins text-cinza-texto md:pb-8">
      <div className="mx-auto w-[calc(100%-28px)] max-w-[1180px] md:w-[calc(100%-40px)]">
        {/* Mobile: identidade em linha própria, Explorar/Participar lado a lado, ligações em 2 colunas */}
        <div className="mb-11 grid grid-cols-2 gap-x-6 gap-y-9 md:mb-16 md:gap-10 lg:grid-cols-[2.5fr_0.7fr_0.9fr_1.5fr] lg:gap-4">
          {/* Identidade */}
          <div className="col-span-2 flex flex-col pr-4 md:col-span-1">
            <BrandLogo
              className="mb-6 gap-4 text-[27px] md:text-[32px]"
              imageClassName="h-[55px] w-[44px] md:h-[60px] md:w-[46px]"
            />
            <p className="m-0 max-w-[460px] text-[15px] leading-relaxed">
              Encontro Nacional de Estudantes de Informática · Faro, Algarve · {EVENT_DATES}.
            </p>
          </div>

          {/* Explorar */}
          <div className="flex flex-col">
            <h4 className={headingClass}>Explorar</h4>
            <ul className={listClass}>
              <li><Link to="/sobre" className="transition-colors hover:text-branco">Sobre</Link></li>
              <li><Link to="/agenda" className="transition-colors hover:text-branco">Agenda</Link></li>
              <li><Link to="/parcerias" className="transition-colors hover:text-branco">Parcerias</Link></li>
            </ul>
          </div>

          {/* Participar */}
          <div className="flex flex-col">
            <h4 className={headingClass}>Participar</h4>
            <ul className={listClass}>
              <li><Link to="/conta" className="transition-colors hover:text-branco">Entrar</Link></li>
              <li><Link to="/bilhetes" className="transition-colors hover:text-branco">Bilhetes</Link></li>
              <li><Link to="/informacao-ajuda" className="transition-colors hover:text-branco">Informação &amp; Ajuda</Link></li>
            </ul>
          </div>

          {/* Organizado por + redes sociais */}
          <div className="col-span-2 grid grid-cols-2 items-start gap-6 border-t border-branco/10 pt-[26px] md:col-span-1 md:flex md:flex-col md:gap-0 md:border-t-0 md:pt-0 lg:border-l lg:pl-10">
            <div className="md:mb-8">
              <span className={labelClass}>Organizado Por</span>
              <img
                src={logoNeei}
                alt="NEEI — Núcleo de Estudantes de Engenharia Informática"
                className="h-auto w-[78px] object-contain md:h-[53px] md:w-auto"
              />
            </div>

            <div>
              <span className={labelClass}>Segue o ENEI</span>
              <div className="flex gap-[7px] md:gap-2.5">
                {socials.map(({ label, href, icon }) => (
                  <a
                    key={label}
                    href={href}
                    aria-label={label}
                    className="flex h-[42px] w-[42px] items-center justify-center rounded border border-branco/10 bg-transparent transition-all hover:border-branco/30 hover:bg-branco/5 hover:text-branco md:h-10 md:w-10"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                      className="h-4 w-4 fill-none stroke-current stroke-[1.5] md:h-[18px] md:w-[18px]"
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

        {/* Barra inferior: alinhada à esquerda no mobile */}
        <div className="flex flex-col items-start justify-between gap-6 border-t border-branco/10 pt-5 text-[12px] text-cinza-subtil md:flex-row md:items-center md:pt-7">
          <p className="m-0">© 2027 ENEI. Todos os direitos reservados.</p>
          <div className="flex flex-wrap justify-start gap-3 md:justify-center md:gap-7">
            <Link to="/termos" className="transition-colors hover:text-branco">Termos e condições</Link>
            <Link to="/privacidade" className="transition-colors hover:text-branco">Política de privacidade</Link>
            <Link to="/acessibilidade" className="transition-colors hover:text-branco">Acessibilidade</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}