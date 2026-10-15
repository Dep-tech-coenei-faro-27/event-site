import type { CSSProperties, ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import SectionHeading from './SectionHeading';
import azulejoPattern from '../assets/azulejo-pattern-transparent.webp';

export interface LegalSection {
    id?: string;
    title: string;
    content: ReactNode;
}

interface LegalPageLayoutProps {
    eyebrow: string;
    title: string;
    lead: string;
    version: string;
    lastUpdated: string;
    /** Data em formato ISO (2026-10-08), para o <time dateTime>. Opcional. */
    lastUpdatedISO?: string;
    sections: LegalSection[];
}


const legalLinks = [
    { label: 'Termos e condições', to: '/termos' },
    { label: 'Política de privacidade', to: '/privacidade' },
    { label: 'Declaração de acessibilidade', to: '/acessibilidade' },
];

const wrap = 'mx-auto w-[calc(100%-28px)] max-w-[1180px] min-[621px]:w-[calc(100%-40px)]';

const gridLines: CSSProperties = {
    backgroundImage:
        'linear-gradient(rgba(26,178,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(26,178,255,0.035) 1px, transparent 1px)',
    backgroundSize: '64px 64px',
    WebkitMaskImage: 'linear-gradient(90deg, transparent, #000 45%, transparent)',
    maskImage: 'linear-gradient(90deg, transparent, #000 45%, transparent)',
};

const sidebarLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3.5 py-4 text-xs font-semibold transition-colors ${
        isActive
            ? 'bg-acento-principal/15 text-branco shadow-[inset_3px_0_0_#1AB2FF]'
            : 'text-cinza-texto hover:bg-acento-principal/10 hover:text-branco'
    }`;

const proseClass = [
    'mt-3.5 max-w-[760px] leading-[1.85] text-cinza-texto',
    '[&_p+p]:mt-4',
    '[&_ul]:mt-4 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:mt-4 [&_ol]:list-decimal [&_ol]:pl-6',
    '[&_li+li]:mt-2',
    '[&_a]:text-acento-forte [&_a]:underline [&_a]:underline-offset-4 [&_a:hover]:text-branco',
    '[&_strong]:text-branco',
].join(' ');

const chipClass =
    'inline-flex items-center gap-1.5 border border-gelo/10 px-3 py-2 text-[10px] uppercase tracking-widest text-cinza-subtil';

const tocItemBorder = (index: number) =>
    index === 0 ? '' : index === 1 ? 'border-t border-gelo/10 md:border-t-0' : 'border-t border-gelo/10';

const sectionId = (section: LegalSection, index: number) => section.id ?? `secao-${index + 1}`;


export default function LegalPageLayout({
    eyebrow,
    title,
    lead,
    version,
    lastUpdated,
    lastUpdatedISO,
    sections,
}: LegalPageLayoutProps) {
    return (
        <div id="conteudo" className="bg-azul-base font-poppins text-branco">
            {/* HERO */}
            <header className="relative overflow-hidden border-b border-acento-principal/[0.42] bg-azul-base bg-[radial-gradient(circle_at_78%_12%,rgba(26,178,255,0.2),transparent_36%)] pt-28">
                <span aria-hidden="true" className="pointer-events-none absolute inset-0" style={gridLines} />

                <div
                    className={`${wrap} relative z-10 flex min-h-[clamp(300px,38vh,420px)] flex-col items-start justify-center py-[58px] md:py-16`}
                >
                    <SectionHeading
                        eyebrow={
                            <span className="mb-4 block font-montserrat text-[11px] font-bold uppercase tracking-[0.14em] text-acento-forte">
                                &lt;{eyebrow} /&gt;
                            </span>
                        }
                        title={title}
                        lead={lead}
                        className="mb-0"
                        classNameTitle="text-[clamp(34px,12vw,52px)] sm:text-[clamp(46px,6.4vw,78px)] leading-[0.98] tracking-[-0.035em] text-balance max-w-[820px]"
                        classNameLead="text-cinza-texto text-[clamp(16px,2vw,19px)] mt-4 max-w-[700px] text-pretty"
                    />

                    <div className="mt-8 flex flex-col flex-wrap items-start gap-2 sm:flex-row" aria-label="Informação do documento">
                        <span className={chipClass}>
                            Versão do texto <strong className="font-bold text-branco">{version}</strong>
                        </span>
                        <span className={chipClass}>
                            Última atualização{' '}
                            <strong className="font-bold text-branco">
                                {lastUpdatedISO ? <time dateTime={lastUpdatedISO}>{lastUpdated}</time> : lastUpdated}
                            </strong>
                        </span>
                    </div>
                </div>
            </header>

            {/* CONTEÚDO */}
            <section
                className="relative overflow-visible"
                style={{
                    backgroundImage: `linear-gradient(rgba(3, 13, 35, 0.92), rgba(3, 13, 35, 0.92)), url(${azulejoPattern})`,
                    backgroundSize: '120px 120px',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'repeat',
                }}
            >
                <div
                    className={`${wrap} grid items-start gap-8 py-[clamp(48px,7vw,80px)] lg:grid-cols-[360px_1fr]`}
                >
                    {/* Barra lateral */}
                    <aside
                        aria-label="Informação legal"
                        className="static w-full overflow-hidden border border-acento-principal/40 bg-azul-painel bg-gradient-to-br from-acento-principal/10 to-transparent lg:sticky lg:top-[calc(76px+24px)] lg:shadow-[0_22px_55px_rgba(0,0,0,0.2)]"
                    >
                        <p className="block py-5 pb-3 pl-6 pr-5 font-montserrat text-[10px] font-bold uppercase tracking-[0.14em] text-cinza-subtil">
                            Nesta área
                        </p>
                        <nav className="grid grid-cols-1 px-2.5 pb-2.5 sm:grid-cols-2 lg:grid-cols-1">
                            {legalLinks.map(({ label, to }) => (
                                <NavLink key={to} to={to} className={sidebarLinkClass}>
                                    {label}
                                </NavLink>
                            ))}
                        </nav>
                        <Link
                            to="/informacao-ajuda"
                            className="block border-t border-acento-principal/10 py-[18px] pl-6 pr-5 text-[11px] font-bold text-acento-forte transition-colors hover:text-branco"
                        >
                            Precisas de ajuda? →
                        </Link>
                    </aside>

                    {/* Documento */}
                    <article className="min-w-0">
                        {/* Índice: gerado a partir das secções */}
                        <nav
                            aria-labelledby="legal-index-title"
                            className="mb-5 grid gap-[clamp(24px,4vw,48px)] border border-gelo/10 bg-azul-painel p-[clamp(24px,4vw,34px)] md:grid-cols-[minmax(190px,0.7fr)_minmax(0,1.3fr)]"
                        >
                            <div>
                                <p className="mb-2 font-montserrat text-[11px] font-bold uppercase tracking-[0.14em] text-acento-forte">
                                    ÍNDICE
                                </p>
                                <h2 id="legal-index-title" className="mt-2 text-[clamp(23px,3vw,30px)] font-bold">
                                    Neste documento
                                </h2>
                            </div>
                            <ol className="m-0 grid list-none gap-x-6 gap-y-0 p-0 md:grid-cols-2">
                                {sections.map((section, index) => (
                                    <li key={sectionId(section, index)}>
                                        <a
                                            href={`#${sectionId(section, index)}`}
                                            className={`flex min-h-[44px] items-center py-2.5 text-[11px] font-semibold text-cinza-texto transition-colors hover:text-branco ${tocItemBorder(index)}`}
                                        >
                                            {section.title}
                                        </a>
                                    </li>
                                ))}
                            </ol>
                        </nav>

                        {/* Secções: uma caixa com linhas de separação */}
                        <div className="divide-y divide-gelo/10 border border-gelo/10 bg-azul-painel">
                            {sections.map((section, index) => (
                                <section
                                    key={sectionId(section, index)}
                                    id={sectionId(section, index)}
                                    className="scroll-mt-[100px] p-[clamp(28px,4vw,40px)]"
                                >
                                    <h2 className="text-[clamp(23px,3vw,30px)] font-bold">{section.title}</h2>
                                    <div className={proseClass}>{section.content}</div>
                                </section>
                            ))}
                        </div>

                        {/* Contacto (comum a todas as páginas legais) */}
                        <div className="mt-6 flex flex-col justify-between gap-7 border border-acento-principal/40 bg-azul-elevado p-7 md:flex-row md:items-center">
                            <SectionHeading
                                eyebrow={
                                    <span className="font-montserrat text-[11px] font-bold uppercase tracking-[0.14em] text-acento-forte">
                                        DÚVIDAS
                                    </span>
                                }
                                title="Podemos ajudar."
                                lead="Consulta a informação prática ou entra em contacto com a organização através da área de ajuda."
                                className="mb-0"
                                classNameTitle="text-[clamp(30px,4vw,40px)]"
                                classNameLead="text-cinza-texto !text-[17px] max-w-[620px]"
                            />

                            <Link
                                to="/informacao-ajuda"
                                className="inline-flex min-h-[48px] shrink-0 items-center justify-center rounded-[3px] border border-transparent bg-acento-principal px-5 font-montserrat text-[12px] font-bold uppercase tracking-[0.055em] text-texto-de-acao transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[5px_5px_0_rgba(26,178,255,0.22)] active:translate-x-0 active:translate-y-0 active:scale-[0.985] active:shadow-[2px_2px_0_rgba(26,178,255,0.18)]"
                            >
                                Informação &amp; Ajuda
                            </Link>
                        </div>
                    </article>
                </div>
            </section>
        </div>
    );
}