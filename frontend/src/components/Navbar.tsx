import { useState, useEffect } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import BrandLogo from './BrandLogo.tsx';

export default function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setIsMenuOpen(false);
  }, [location]);

  useEffect(() => {
    if (isMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => { document.body.style.overflow = 'unset'; }
  }, [isMenuOpen]);

  const navLinks = [
    { name: 'Sobre', path: '/sobre' },
    { name: 'Agenda', path: '/agenda' },
    { name: 'Equipa', path: '/equipa' },
    { name: 'Parcerias', path: '/parcerias' },
    { name: 'Informação & Ajuda', path: '/informacao-ajuda' },
    { name: 'Bilhetes', path: '/bilhetes' },
  ];

  return (
    <header className="fixed top-0 inset-x-0 z-[100] h-[64px] md:h-[76px] border-b border-acento-principal/15 bg-azul-noite/30 backdrop-blur-[22px] backdrop-saturate-[1.35] shadow-[0_8px_30px_rgba(0,0,0,0.08)] font-poppins">
      <div className="max-w-[1180px] mx-auto w-[calc(100%-28px)] md:w-[calc(100%-40px)] h-full flex items-center justify-between gap-4">
        
        <div className="flex-shrink-0 z-50">
          <BrandLogo />
        </div>

        <nav
          className={`md:static md:flex md:items-center md:justify-center md:bg-transparent md:h-auto md:p-0 md:max-h-none md:overflow-visible md:border-none fixed inset-x-0 top-[64px] bg-azul-base/95 px-5 flex flex-col transition-all duration-300 overflow-hidden text-[13px] text-nevoa-azul ${
            isMenuOpen ? 'max-h-[calc(100vh-64px)] py-[18px] border-b border-branco/10' : 'max-h-0 border-b-0 py-0'
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

            <Link
              to="/conta"
              className="md:hidden w-full mt-4 min-h-[40px] inline-flex items-center justify-center px-[18px] rounded-full text-branco font-bold border border-acento-principal/50 bg-acento-principal/10 transition-all duration-300 hover:bg-[#0d3b66] hover:border-[#00b4d8]"
            >
              Entrar
            </Link>
          </div>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            to="/conta"
            className="hidden md:inline-flex min-h-[40px] items-center justify-center px-4 rounded-full border border-acento-principal/50 bg-acento-principal/10 text-branco text-[13px] font-bold transition-all duration-300 hover:bg-[#0d3b66] hover:border-[#00b4d8]"
          >
            Entrar
          </Link>

          <button
            type="button"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-expanded={isMenuOpen}
            aria-label="Menu de navegação"
            className="md:hidden relative flex-none w-[42px] h-[42px] border border-acento-principal/40 rounded-xl bg-transparent text-branco flex items-center justify-center z-50"
          >
            <svg viewBox="0 0 24 24" className="w-[22px] h-[22px] fill-none stroke-current stroke-2" strokeLinecap="round">
              {isMenuOpen ? (
                <path d="m6 6 12 12M18 6 6 18" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" />
              )}
            </svg>
          </button>
        </div>

      </div>
    </header>
  );
}