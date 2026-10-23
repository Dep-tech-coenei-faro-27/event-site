import React from 'react'
interface SectionHeadingProps {
  eyebrow?: React.ReactNode; //Mensagem acima do titulo
  title: string; //Titulo
  lead?: string; // Mensagem abaixo do titulo
  align?: 'left' | 'center'
  className?: string;
  classNameTitle?: string; 
  classNameLead?: string;
  /** Nível do título: 1 só quando é o título da página. */
  level?: 1 | 2;
}

export default function SectionHeading({ eyebrow, title, lead, align = 'left', className = 'text-[clamp(40px,6vw,70px)] tracking-tight leading-[1.06]', classNameTitle, classNameLead = 'text-slate-300', level = 2 }: SectionHeadingProps) {
  const Title = level === 1 ? 'h1' : 'h2';
  const alignment = align === 'center' ? 'text-center mx-auto' : 'text-left';

  return (
    <div className={`mb-11 ${alignment} ${className}`}>
      {eyebrow && (
        <div> {eyebrow}</div>
      )}
      <Title className={`m-0 font-poppins font-bold ${classNameTitle}`}>
        {title}
      </Title>
      {lead && (
        <p className={`leading-relaxed mt-5 text-[clamp(24px,6vw,24px)] max-w-[720px] ${classNameLead} ${align === 'center' ? 'mx-auto' : ''}`}>
          {lead}
        </p>
      )}
    </div>
  );
}