import React from 'react';
import { Link } from 'react-router-dom';

interface PrimaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text: string;
  className?: string;
  to?: string; // se existir, navega para este URL
}

const base = 'btn btn--primary';

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
