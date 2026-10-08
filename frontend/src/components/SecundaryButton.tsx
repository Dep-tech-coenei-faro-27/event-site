import React from 'react';
import { Link } from 'react-router-dom';

interface SecondaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text: string;
  className?: string;
  to?: string; // se existir, navega para este URL
}

const base =
  'min-h-[46px] px-6 py-0 inline-flex items-center justify-center gap-2 rounded-full border border-white/25 bg-white/5 text-white font-montserrat font-bold text-[14px] cursor-pointer transition-[transform,background-color,border-color] duration-200 hover:-translate-y-0.5 hover:border-white/55 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed';

export default function SecondaryButton({
  text,
  className = '',
  type = 'button',
  to,
  ...props
}: SecondaryButtonProps) {
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