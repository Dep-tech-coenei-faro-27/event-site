import { Link } from 'react-router-dom';
import BrandLogo from './BrandLogo';
import logoNeei from '../assets/neei-logo.webp';

export default function Footer() {
  return (
    <footer className="bg-azul-noite pt-16 pb-8 font-poppins text-cinza-texto border-t border-branco/5">
      <div className="max-w-[1180px] mx-auto w-[calc(100%-28px)] md:w-[calc(100%-40px)]">
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[2.5fr_0.7fr_0.9fr_1.5fr] gap-10 lg:gap-4 mb-16">
          
          <div className="flex flex-col pr-4">
            <BrandLogo className="text-[32px] gap-4 mb-6" imageClassName="w-[46px] h-[60px]" />
            <p className="text-[15px] leading-relaxed max-w-[460px] m-0">
              Encontro Nacional de Estudantes de Informática · Faro, Algarve · 8–11 abril 2027.
            </p>
          </div>

          <div className="flex flex-col">
            <h4 className="text-branco font-bold text-[15px] mb-5 m-0">Explorar</h4>
            <ul className="flex flex-col gap-2.5 text-[14px] m-0 p-0 list-none">
              <li><Link to="/sobre" className="hover:text-branco transition-colors">Sobre</Link></li>
              <li><Link to="/agenda" className="hover:text-branco transition-colors">Agenda</Link></li>
              <li><Link to="/parcerias" className="hover:text-branco transition-colors">Parcerias</Link></li>
            </ul>
          </div>

          <div className="flex flex-col">
            <h4 className="text-branco font-bold text-[15px] mb-5 m-0">Participar</h4>
            <ul className="flex flex-col gap-2.5 text-[14px] m-0 p-0 list-none">
              <li><Link to="/conta" className="hover:text-branco transition-colors">Entrar</Link></li>
              <li><Link to="/bilhetes" className="hover:text-branco transition-colors">Bilhetes</Link></li>
              <li><Link to="/informacao-ajuda" className="hover:text-branco transition-colors">Informação & Ajuda</Link></li>
            </ul>
          </div>

          <div className="flex flex-col lg:pl-10 lg:border-l border-branco/10">
            <div className="mb-8">
              <span className="block mb-3 text-cinza-subtil font-montserrat font-bold text-[10px] tracking-[0.16em] uppercase">
                Organizado Por
              </span>
              <img src={logoNeei} alt="Logótipo NEEI" className="h-[53px] object-contain" />
            </div>
            
            <div>
              <span className="block mb-3 text-cinza-subtil font-montserrat font-bold text-[10px] tracking-[0.16em] uppercase">
                Segue o ENEI
              </span>
              <div className="flex gap-2.5">
                <a href="#" className="w-10 h-10 flex items-center justify-center border border-branco/10 rounded bg-transparent hover:text-branco hover:border-branco/30 hover:bg-branco/5 transition-all">
                  <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] fill-none stroke-current stroke-[1.5]" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
                  </svg>
                </a>
                <a href="#" className="w-10 h-10 flex items-center justify-center border border-branco/10 rounded bg-transparent hover:text-branco hover:border-branco/30 hover:bg-branco/5 transition-all">
                  <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] fill-none stroke-current stroke-[1.5]" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path>
                  </svg>
                </a>
                <a href="#" className="w-10 h-10 flex items-center justify-center border border-branco/10 rounded bg-transparent hover:text-branco hover:border-branco/30 hover:bg-branco/5 transition-all">
                  <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] fill-none stroke-current stroke-[1.5]" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path>
                    <rect x="2" y="9" width="4" height="12"></rect>
                    <circle cx="4" cy="4" r="2"></circle>
                  </svg>
                </a>
              </div>
            </div>
          </div>

        </div>

        <div className="pt-7 border-t border-branco/10 flex flex-col md:flex-row justify-between items-center gap-6 text-[12px] text-cinza-subtil">
          <p className="m-0">© 2027 ENEI. Todos os direitos reservados.</p>
          <div className="flex flex-wrap justify-center gap-7">
            <Link to="/termos" className="hover:text-branco transition-colors">Termos e condições</Link>
            <Link to="/privacidade" className="hover:text-branco transition-colors">Política de privacidade</Link>
            <Link to="/acessibilidade" className="hover:text-branco transition-colors">Acessibilidade</Link>
          </div>
        </div>

      </div>
    </footer>
  );
}