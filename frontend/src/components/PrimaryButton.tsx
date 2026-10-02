import React from 'react';

interface PrimaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text: string;
  className?: string;
}

export default function PrimaryButton({
  text,
  className = '',
  type = 'button',
  ...props
}: PrimaryButtonProps) {
  return (
    <button
      type={type}
      className={`px-6 py-3 rounded-full bg-[#1AB2FF] hover:bg-[#23CAFF] text-[#02101C] font-montserrat font-bold text-sm sm:text-base transition-all duration-200 shadow-lg shadow-[#1AB2FF]/25 hover:shadow-[#23CAFF]/35 active:scale-95 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      {...props}
    >
      {text}
    </button>
  );
}