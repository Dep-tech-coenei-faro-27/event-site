import React from 'react';

interface SecondaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text: string;
  className?: string;
}

export default function SecondaryButton({
  text,
  className = '',
  type = 'button',
  ...props
}: SecondaryButtonProps) {
  return (
    <button
      type={type}
      className={`min-h-[46px] px-6 py-0 inline-flex items-center justify-center gap-2 rounded-full border border-white/25 bg-white/5 text-white font-montserrat font-bold text-[14px] cursor-pointer transition-[transform,background-color,border-color] duration-200 hover:-translate-y-0.5 hover:border-white/55 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      {...props}
    >
      {text}
    </button>
  );
}