import type { ReactNode } from 'react';
import Eyebrow from '../EyeBrow';
import { panelClass, panelTitleClass } from './AccountStyles';

interface AccountPanelProps {
  id?: string;
  eyebrow: string;
  title: string;
  description?: string;
  /** Elemento à direita do cabeçalho (por exemplo, um botão). Fica por baixo em mobile. */
  action?: ReactNode;
  className?: string;
  children?: ReactNode;
}

/** Caixa padrão da área pessoal: eyebrow, título, descrição e conteúdo. */
export default function AccountPanel({
  id,
  eyebrow,
  title,
  description,
  action,
  className = '',
  children,
}: AccountPanelProps) {
  return (
    <article id={id} className={`${panelClass} ${className}`}>
      <header
        className={`flex flex-col gap-5 min-[621px]:flex-row min-[621px]:items-start min-[621px]:justify-between ${
          children ? 'mb-5' : ''
        }`}
      >
        <div>
          <Eyebrow text={eyebrow} />
          <h2 className={panelTitleClass}>{title}</h2>
          {description && <p className="mb-0 mt-1.5 text-[13px] text-cinza-texto">{description}</p>}
        </div>
        {action}
      </header>
      {children}
    </article>
  );
}