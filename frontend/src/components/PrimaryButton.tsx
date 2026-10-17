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
      className={`btn btn--primary ${className}`}
      {...props}
    >
      {text}
    </button>
  );
}