import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import Eyebrow from '../EyeBrow';
import { usePageMeta } from '../../utils/usePageMeta';
import { useAuth } from '../../utils/useAuth';
import { BORDER } from './AccountStyles';

interface AccountLayoutProps {
  /** <title> e meta description da página */
  metaTitle: string;
  metaDescription: string;
  /** Hero */
  eyebrow: string;
  title: string;
  lead: string;
  children: ReactNode;
}

function initialsOf(name: string, email: string): string {
  const source = name.trim() || email.split('@')[0] || '?';
  const parts = source.split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : source.slice(0, 2);
  return letters.toUpperCase();
}

const iconProps = {
  className: 'size-[18px] shrink-0',
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  'aria-hidden': true,
} as const;

// Páginas da área pessoal. Ajusta os caminhos às rotas que registares.
const accountNav = [
  {
    label: 'Visão geral',
    to: '/perfil',
    icon: (
      <svg {...iconProps}>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    label: 'Dados pessoais',
    to: '/conta/dados',
    icon: (
      <svg {...iconProps}>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M5 20a7 7 0 0 1 14 0" />
      </svg>
    ),
  },
  {
    label: 'Segurança',
    to: '/conta/seguranca',
    icon: (
      <svg {...iconProps}>
        <path d="M12 3 5 6v5c0 4.5 2.8 7.8 7 10 4.2-2.2 7-5.5 7-10V6z" />
        <path d="m9.5 12 1.7 1.7 3.6-4" />
      </svg>
    ),
  },
];

const navLink =
  'flex items-center gap-3 border-l-[3px] border-transparent px-5 py-3 text-[13px] font-medium text-cinza-texto transition-colors hover:bg-white/5 hover:text-white max-[900px]:min-w-max max-[900px]:border-b-[3px] max-[900px]:border-l-0';
const navLinkActive =
  '!border-acento-principal bg-[rgba(26,178,255,0.07)] !text-white hover:bg-[rgba(26,178,255,0.1)]';

/**
 * Estrutura comum das páginas da área pessoal: hero + barra lateral + conteúdo.
 * Cada página passa só o hero e o conteúdo (children).
 */
export default function AccountLayout({
  metaTitle,
  metaDescription,
  eyebrow,
  title,
  lead,
  children,
}: AccountLayoutProps) {
  usePageMeta(metaTitle, metaDescription);

  const { user: me, logout } = useAuth();
  const name = me?.name ?? '';
  const email = me?.email ?? '';

  return (
    <div className="azulejo-bg min-h-screen bg-azul-base pt-16 font-poppins leading-[1.65] text-white min-[621px]:pt-[76px] max-[620px]:pb-[84px]">
      <div id="conteudo" className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="azulejo-bg pointer-events-none absolute inset-0 bg-acento-principal opacity-[0.025]"
        />

        {/* Hero */}
        <header
          className={`relative z-[1] border-b ${BORDER} bg-[radial-gradient(circle_at_78%_12%,rgba(26,178,255,0.2),transparent_36%)] pb-[clamp(32px,4.5vw,48px)] pt-[clamp(40px,6vw,76px)]`}
        >
          <div className="mx-auto w-[min(calc(100%-28px),1180px)] min-[621px]:w-[min(calc(100%-40px),1180px)]">
            <Eyebrow text={eyebrow} />
            <h1 className="text-[clamp(32px,5vw,56px)] font-bold leading-[1.06] tracking-[-0.045em]">{title}</h1>
            <p className="mt-3.5 max-w-[680px] text-[clamp(15px,1.8vw,18px)] text-cinza-texto">{lead}</p>
          </div>
        </header>

        {/* Barra lateral + conteúdo */}
        <section className="relative z-[1] py-[clamp(36px,5vw,64px)]">
          <div className="mx-auto grid w-[min(calc(100%-28px),1180px)] gap-6 min-[621px]:w-[min(calc(100%-40px),1180px)] min-[901px]:grid-cols-[340px_minmax(0,1fr)]">
            <aside className={`flex h-fit flex-col border ${BORDER} bg-azul-painel`}>
              <div className={`flex items-center gap-3.5 border-b ${BORDER} p-5`}>
                <div className="flex size-12 shrink-0 items-center justify-center border border-acento-principal/50 bg-acento-principal/10 text-[15px] font-bold text-acento-principal">
                  {initialsOf(name, email)}
                </div>
                <div className="flex min-w-0 flex-col">
                  <strong className="truncate text-[15px] font-bold leading-snug text-white">
                    {name.trim() || 'Participante'}
                  </strong>
                  <p className="m-0 truncate text-[12px] text-cinza-texto">{email || 'participante@exemplo.pt'}</p>
                  <span className="mt-1 inline-flex items-center gap-1.5 text-[11px] font-semibold text-[#d7e3f4]">
                    <span className={`size-2 rounded-full ${me?.is_verified ? 'bg-[#10b981]' : 'bg-areia'}`} />
                    {me?.is_verified ? 'Email verificado' : 'Email por verificar'}
                  </span>
                </div>
              </div>

              <nav aria-label="Área pessoal" className="flex flex-col py-2 max-[900px]:flex-row max-[900px]:overflow-x-auto">
                {accountNav.map(({ label, to, icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) => `${navLink} ${isActive ? navLinkActive : ''}`}
                  >
                    {icon}
                    <span>{label}</span>
                  </NavLink>
                ))}

                <div className={`my-1.5 border-b ${BORDER} max-[900px]:hidden`} />

                <button
                  type="button"
                  onClick={() => void logout()}
                  className={`${navLink} w-full cursor-pointer bg-transparent text-left`}
                >
                  <svg {...iconProps}>
                    <path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9" />
                  </svg>
                  <span>Sair</span>
                </button>
              </nav>
            </aside>

            <div className="grid gap-[18px]">{children}</div>
          </div>
        </section>
      </div>
    </div>
  );
}