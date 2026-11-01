import { useState, useEffect, useRef } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import BrandLogo from './BrandLogo.tsx';
import { useAuth } from '../utils/useAuth';
import { useMediaQuery } from '../utils/useMediaQuery';

const navLinks = [
  { name: 'Sobre', path: '/sobre' },
  { name: 'Agenda', path: '/agenda' },
  { name: 'Equipa', path: '/equipa' },
  { name: 'Informações e ajuda', path: '/informacao-ajuda' },
  { name: 'Bilhetes', path: '/bilhetes' }
];

const LOGIN_PATH = '/conta';
const NAV_ID = 'navegacao-principal';
// Abaixo de `md` (768 px) a navegação é o menu que abre e fecha.
const MOBILE_QUERY = '(max-width: 767px)';
const ACCOUNT_PATH = '/perfil';

const loginDesktopClass =
  'hidden md:inline-flex min-h-[40px] items-center justify-center px-4 rounded-full border border-acento-principal/50 bg-acento-principal/10 text-branco text-[13px] font-bold transition-all duration-300 hover:bg-[#0d3b66] hover:border-[#00b4d8] cursor-pointer';
const loginMobileClass =
  'md:hidden w-full mt-4 min-h-[40px] inline-flex items-center justify-center px-[18px] rounded-full text-branco font-bold border border-acento-principal/50 bg-acento-principal/10 transition-all duration-300 hover:bg-[#0d3b66] hover:border-[#00b4d8] cursor-pointer';

const userDesktopClass =
  'hidden md:inline-flex items-center gap-2.5 rounded-full border border-acento-principal/45 bg-acento-principal/10 py-1 pl-1.5 pr-4 text-branco transition-all duration-300 hover:bg-[#0d3b66] hover:border-[#00b4d8] cursor-pointer';
const userMobileClass =
  'md:hidden w-full mt-4 inline-flex items-center gap-3 rounded-full border border-acento-principal/45 bg-acento-principal/10 p-1.5 pr-5 text-branco transition-all duration-300 hover:bg-[#0d3b66] hover:border-[#00b4d8] cursor-pointer';

function initialsOf(name: string, email: string): string {
  const source = name.trim() || email.split('@')[0] || '?';
  const parts = source.split(/\s+/).filter(Boolean);
  const letters =
    parts.length > 1
      ? parts[0][0] + parts[parts.length - 1][0]
      : source.slice(0, 2);
  return letters.toUpperCase();
}

function AccountActions({ mobile = false }: { mobile?: boolean }) {
  const { user, loading } = useAuth();

  if (loading) return null;

  if (!user) {
    return (
      <Link to={LOGIN_PATH} className={mobile ? loginMobileClass : loginDesktopClass}>
        Entrar
      </Link>
    );
  }

  const firstName = user.name.trim().split(/\s+/)[0] || 'Participante';
  const initials = initialsOf(user.name, user.email);

  return (
    <Link
      to={ACCOUNT_PATH}
      aria-label={`Abrir área pessoal de ${firstName}`}
      className={mobile ? userMobileClass : userDesktopClass}
    >
      <span
        aria-hidden="true"
        className="grid size-8 shrink-0 place-items-center rounded-full border border-acento-principal/50 bg-acento-principal/20 font-montserrat text-[11px] font-extrabold text-acento-forte"
      >
        {initials}
      </span>
      <span className="flex flex-col text-left leading-tight">
        <strong className="max-w-[130px] truncate text-[12px] font-bold text-branco">
          {firstName}
        </strong>
        <small className="font-montserrat text-[9px] font-bold uppercase tracking-[0.08em] text-acento-forte">
          Área pessoal
        </small>
      </span>
    </Link>
  );
}

export default function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  // Fecha o menu quando a rota muda. O estado ajusta-se durante a renderização (e não num
  // efeito), que é o padrão que o React recomenda para reagir a uma mudança de valor.
  const [menuLocation, setMenuLocation] = useState(location);
  if (location !== menuLocation) {
    setMenuLocation(location);
    setIsMenuOpen(false);
  }

  useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; }
  }, [isMenuOpen]);

  // Escape fecha o menu aberto e devolve o foco ao botão que o abriu.
  useEffect(() => {
    if (!isMenuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setIsMenuOpen(false);
      menuButtonRef.current?.focus();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [isMenuOpen]);

  return (
    <header className="site-header fixed top-0 inset-x-0 z-[100] h-[64px] md:h-[76px] border-b border-acento-principal/15 bg-azul-noite/30 backdrop-blur-[22px] backdrop-saturate-[1.35] shadow-[0_8px_30px_rgba(0,0,0,0.08)] font-poppins">
      <div className="max-w-[1180px] mx-auto w-[calc(100%-40px)] h-full flex items-center justify-between gap-4">

        <div className="flex-shrink-0 z-50">
          <BrandLogo />
        </div>

        {/* O botão vem antes da <nav> no documento: aberto o menu, o Tab seguinte entra nos links. */}
        <button
          ref={menuButtonRef}
          type="button"
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          aria-expanded={isMenuOpen}
          aria-controls={NAV_ID}
          aria-label="Menu de navegação"
          className="md:hidden relative flex-none ml-auto w-[42px] h-[42px] border border-acento-principal/40 rounded-xl bg-transparent text-branco flex items-center justify-center z-50"
        >
          <svg viewBox="0 0 24 24" className="w-[22px] h-[22px] fill-none stroke-current stroke-2" strokeLinecap="round">
            {isMenuOpen ? (
              <path d="m6 6 12 12M18 6 6 18" />
            ) : (
              <path d="M4 7h16M4 12h16M4 17h16" />
            )}
          </svg>
        </button>

        <nav
          id={NAV_ID}
          aria-label="Principal"
          // Fechado no telemóvel, o menu está só encolhido: `inert` tira os links da ordem de tabulação.
          inert={isMobile && !isMenuOpen}
          className={`md:static md:flex md:items-center md:justify-center md:bg-transparent md:h-auto md:p-0 md:max-h-none md:overflow-visible md:border-none fixed inset-x-0 top-[64px] bg-azul-base/95 px-5 flex flex-col transition-all duration-300 overflow-x-hidden text-[13px] text-nevoa-azul ${isMenuOpen ? 'max-h-[calc(100vh-64px)] overflow-y-auto py-[18px] border-b border-branco/10' : 'max-h-0 overflow-y-hidden border-b-0 py-0'
            }`}
        >
          <div className="flex flex-col md:flex-row md:items-center md:gap-7 w-full md:w-auto">
            {navLinks.map((link) => (
              <NavLink
                key={link.name}
                to={link.path}
                className={({ isActive }) => `
                  relative block transition-colors duration-200 group
                  py-[13px] px-1 md:py-[9px] md:px-0 border-b border-branco/5 md:border-none
                  ${isActive ? 'text-branco' : 'hover:text-branco'}
                `}
              >
                {({ isActive }) => (
                  <>
                    {link.name}
                    <span
                      className={`
                        hidden md:block absolute left-0 bottom-[2px] h-[1px] bg-acento-principal transition-all duration-200
                        ${isActive ? 'right-0' : 'right-full group-hover:right-0'}
                      `}
                    ></span>
                  </>
                )}
              </NavLink>
            ))}

            {/* Conta no menu mobile */}
            <AccountActions mobile />
          </div>
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {/* Conta no desktop */}
          <AccountActions />
        </div>

      </div>
    </header>
  );
}
