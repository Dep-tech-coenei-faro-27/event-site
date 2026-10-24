import type { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import '../legal.css';
import { useBodyPage } from '../utils/useBodyPage';
import { usePageMeta } from '../utils/usePageMeta';

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

const sectionId = (section: LegalSection, index: number) => section.id ?? `secao-${index + 1}`;

/**
 * Páginas legais no desenho novo (`ui-ux/termos`, `privacidade`, `acessibilidade`): o mesmo documento
 * com barra lateral, índice e secções. O CSS (`legal.css`) é gerado do protótipo e limitado a
 * `body[data-page="legal"]`. O texto de cada página vem das próprias páginas, por `sections`.
 */
export default function LegalPageLayout({
    eyebrow,
    title,
    lead,
    version,
    lastUpdated,
    lastUpdatedISO,
    sections,
}: LegalPageLayoutProps) {
    useBodyPage('legal');
    usePageMeta(`${title} · ENEI 2027`, lead);

    return (
        <>
            <header className="page-hero legal-hero">
                <div className="container">
                    <p className="eyebrow">&lt;{eyebrow} /&gt;</p>
                    <h1>{title}</h1>
                    <p className="lead">{lead}</p>
                    <div className="legal-meta" aria-label="Informação do documento">
                        <span>
                            Versão do texto <strong>{version}</strong>
                        </span>
                        <span>
                            Última atualização <time dateTime={lastUpdatedISO}>{lastUpdated}</time>
                        </span>
                    </div>
                </div>
            </header>

            <section className="section legal-section-wrap">
                <div className="container legal-layout">
                    <aside className="legal-sidebar" aria-label="Informação legal">
                        <p className="footer-label">Nesta área</p>
                        <nav>
                            {legalLinks.map((link) => (
                                <NavLink key={link.to} to={link.to}>
                                    {link.label}
                                </NavLink>
                            ))}
                        </nav>
                        <Link className="legal-help" to="/informacao-ajuda">
                            Precisas de ajuda? →
                        </Link>
                    </aside>

                    <article className="legal-document">
                        <nav className="legal-toc" aria-labelledby="legal-index-title">
                            <div className="legal-toc__heading">
                                <p className="eyebrow">ÍNDICE</p>
                                <h2 id="legal-index-title">Neste documento</h2>
                            </div>
                            <ol>
                                {sections.map((section, index) => (
                                    <li key={sectionId(section, index)}>
                                        <a href={`#${sectionId(section, index)}`}>{section.title}</a>
                                    </li>
                                ))}
                            </ol>
                        </nav>

                        {sections.map((section, index) => (
                            <section className="legal-section" id={sectionId(section, index)} key={sectionId(section, index)}>
                                <h2>{section.title}</h2>
                                {section.content}
                            </section>
                        ))}

                        <div className="legal-contact">
                            <div>
                                <p className="eyebrow">DÚVIDAS</p>
                                <h2>Podemos ajudar.</h2>
                                <p>Consulta a informação prática ou entra em contacto com a organização através da área de ajuda.</p>
                            </div>
                            <Link className="btn btn--primary" to="/informacao-ajuda">
                                Informação &amp; Ajuda
                            </Link>
                        </div>
                    </article>
                </div>
            </section>
        </>
    );
}
