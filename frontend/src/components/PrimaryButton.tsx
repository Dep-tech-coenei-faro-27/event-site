import React from 'react';
import { Link } from 'react-router-dom';

interface PrimaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text: string;
  className?: string;
  to?: string; // se existir, navega para este URL
}

const base =
  'inline-flex items-center justify-center px-6 py-3 rounded-full bg-[#1AB2FF] hover:bg-[#23CAFF] text-[#02101C] font-montserrat font-bold text-sm sm:text-base transition-all duration-200 hover:shadow-[#23CAFF]/35 active:scale-95 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed';

export default function PrimaryButton({
  text,
  className = '',
  type = 'button',
  to,
  ...props
}: PrimaryButtonProps) {
  if (to) {
    return (
      <Link to={to} className={`${base} ${className}`}>
        {text}
      </Link>
    );
  }

  return (
    <button type={type} className={`${base} ${className}`} {...props}>
      {text}
    </button>
  );
}
