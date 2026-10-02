import { Link } from 'react-router-dom';
import logoEnei from '../assets/ENEI-logo.svg';
interface BrandLogoProps {
  className?: string;
  imageClassName?: string;
}

function BrandLogo({ className = '', imageClassName = 'w-[27px] h-[34px] md:w-[36px] md:h-[46px]' }: BrandLogoProps) {
    return (
        <Link to="/" className={`inline-flex items-center gap-[11px] font-poppins font-extrabold text-[23px] leading-none text-branco hover:opacity-80 transition-opacity ${className}`} >
            <img src={logoEnei} alt="Logo Nei" className={`${imageClassName} object-contain`}/> 
            <span> ENEI</span>
        </Link>
    );
}

export default BrandLogo;
