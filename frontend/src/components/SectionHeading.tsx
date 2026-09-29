import React from 'react'
interface SectionHeadingProps {
    eyebrow?: React.ReactNode; //Mensagem acima do titulo
    title: string; //Titulo
    lead?: string; // Mensagem abaixo do titulo
    align?: 'left' | 'center'
    className?: string; //Estilos tailwind 
}

export default function SectionHeading({ eyebrow, title, lead, align = 'left', className = '' }: SectionHeadingProps) {
  const alignment = align === 'center' ? 'text-center mx-auto' : 'text-left';

  return (
    <div className={`mb-11 ${alignment} ${className}`}>
      {eyebrow && (
        <div> {eyebrow}</div> 
      )}

      <h2 className="m-0 font-poppins font-bold text-[clamp(30px,4vw,52px)] tracking-[-0.045em] leading-[1.06]">
        {title}
      </h2>
      {lead && (
        <p className={`mt-5 text-cinza-texto text-[clamp(17px,2vw,20px)] max-w-[720px] ${align === 'center' ? 'mx-auto' : ''}`}>
          {lead}
        </p>
      )}
    </div>
  );
}