import type { MouseEvent } from 'react';
import { Link, useLocation } from 'react-router-dom';
import logoEnei from '../assets/ENEI-logo.svg';
interface BrandLogoProps {
  className?: string;
  imageClassName?: string;
}

function BrandLogo({ className = '', imageClassName = 'w-[27px] h-[34px] md:w-[36px] md:h-[46px]' }: BrandLogoProps) {
    const { pathname, search, hash } = useLocation();

    // Já na página inicial o router não faz nada (o endereço é o mesmo), por isso o logótipo
    // «não saltava» para o início: aqui sobe-se à mão. Com Ctrl, Cmd, Shift ou o botão do meio
    // deixa-se o browser abrir a ligação como sempre.
    const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
        const alreadyHome = pathname === '/' && !search && !hash;
        const modified = event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
        if (!alreadyHome || modified) return;
        event.preventDefault();
        const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top: 0, left: 0, behavior: reduced ? 'auto' : 'smooth' });
    };

    return (
        <Link to="/" aria-label="ENEI — página inicial" onClick={handleClick} className={`brand inline-flex items-center gap-[11px] font-poppins font-extrabold text-[23px] leading-none text-branco ${className}`} >
            <img src={logoEnei} alt="Logótipo do ENEI" className={`${imageClassName} object-contain`}/>
            <span> ENEI</span>
        </Link>
    );
}

export default BrandLogo;
