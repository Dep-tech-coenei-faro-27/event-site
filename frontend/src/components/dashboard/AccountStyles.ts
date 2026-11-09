// Estilos partilhados pelas páginas da área pessoal.
// Ficam num .ts (sem componentes) para não violar a regra react-refresh/only-export-components.

export const BORDER = 'border-[rgba(215,227,244,0.1)]';

// Caixa de conteúdo (cartão da área pessoal)
export const panelClass = `border ${BORDER} bg-azul-painel px-5 py-6 min-[621px]:p-7`;

// Título dentro de uma caixa
export const panelTitleClass =
  'text-[clamp(24px,3vw,34px)] font-bold leading-[1.08] tracking-[-0.04em] text-white';