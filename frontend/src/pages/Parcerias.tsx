import type { CSSProperties, ReactNode } from 'react';
import PageHeader from '../components/PageHeader';
import SectionHeading from '../components/SectionHeading';
import EyeBrow from '../components/EyeBrow';
import faroOldTown from '../assets/faro-old-town.webp';
import azulejoPattern from '../assets/azulejo-pattern-transparent.webp';
import PrimaryButton from '../components/PrimaryButton';
import SecundaryButton from '../components/SecundaryButton';
import Tile, { IconBox, type Tone } from '../components/Tile';


interface TileItem {
    title: string;
    text: string;
    tone: Tone;
    icon: ReactNode;
}

interface PartnerTier {
    name: string;
    color: string; // cor do nível (borda, nome, padrão)
    title: string;
    items: string[];
}


const partnershipBenefits: TileItem[] = [
    {
        title: 'Acesso ao talento',
        text: 'Contacto direto com estudantes de informática de todo o país.',
        tone: 'cyan',
        icon: (
            <>
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
            </>
        ),
    },
    {
        title: 'Visibilidade',
        text: 'Presença integrada antes, durante e depois do evento.',
        tone: 'sand',
        icon: (
            <>
                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                <circle cx="12" cy="12" r="3" />
            </>
        ),
    },
    {
        title: 'Networking',
        text: 'Relações com academia, comunidades e outras empresas.',
        tone: 'periwinkle',
        icon: (
            <>
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </>
        ),
    },
    {
        title: 'Impacto',
        text: 'Apoio concreto ao desenvolvimento da comunidade tecnológica.',
        tone: 'coral',
        icon: (
            <>
                <circle cx="12" cy="12" r="10" />
                <circle cx="12" cy="12" r="6" />
                <circle cx="12" cy="12" r="2" />
            </>
        ),
    },
];

const tiers: PartnerTier[] = [
    {
        name: 'Diamante',
        color: '#1AB2FF',
        title: 'Presença principal',
        items: ['Ativação de marca', 'Espaço de exposição', 'Participação no programa', 'Comunicação premium'],
    },
    {
        name: 'Ouro',
        color: '#F4C542',
        title: 'Grande visibilidade',
        items: ['Espaço de exposição', 'Presença editorial', 'Atividades com participantes', 'Marca em suportes'],
    },
    {
        name: 'Prata',
        color: '#C8D0DA',
        title: 'Ligação à comunidade',
        items: ['Presença de marca', 'Divulgação digital', 'Acesso ao evento', 'Networking'],
    },
    {
        name: 'Bronze',
        color: '#D18B53',
        title: 'Apoio ao encontro',
        items: ['Logótipo no site', 'Menção institucional', 'Acesso ao evento', 'Comunidade'],
    },
];

const supporters: string[] = [
    'UAlg',
    'FCT UAlg',
    'AAUAlg',
    'NEEC',
    'Algarve Evolution',
    'UAlg Cria',
    'CM Faro',
    'CM Loulé',
    'CM Portimão',
    'CM Lagos',
    'CM Aljustrel',
    'CM São Brás',
    'Tomás Cabreira',
];


const wrap = 'mx-auto w-[calc(100%-40px)] max-w-[1180px]';
const sectionY = 'py-[clamp(72px,9vw,124px)]';
const h2Center = 'mt-1 font-extrabold text-4xl sm:text-4xl lg:text-5xl leading-[1.08] tracking-tight text-branco';

const btn =
    'inline-flex min-h-[46px] items-center justify-center rounded-full border px-6 text-sm font-bold transition duration-200 hover:-translate-y-0.5';
const btnCtaDark = `${btn} border-white/15 bg-azul-painel text-branco hover:bg-azul-elevado`;

const centerEyebrow = (text: string) => (
    <p className="m-0 mb-3.5 font-montserrat text-[11px] font-bold uppercase leading-[1.4] tracking-[0.16em] text-acento-forte">
        &lt;{text} /&gt;
    </p>
);

const patternMask = (size: number, position = 'center'): CSSProperties => ({
    WebkitMaskImage: `url(${azulejoPattern})`,
    maskImage: `url(${azulejoPattern})`,
    WebkitMaskSize: `${size}px ${size}px`,
    maskSize: `${size}px ${size}px`,
    WebkitMaskPosition: position,
    maskPosition: position,
    WebkitMaskRepeat: 'repeat',
    maskRepeat: 'repeat',
});


const TierCard = ({ name, color, title, items }: PartnerTier) => (
    <article
        style={{ '--tier-color': color } as CSSProperties}
        className="relative grid grid-cols-1 gap-2.5 overflow-hidden rounded-l-[4px] rounded-r-[22px] border border-l-[5px] border-[color:color-mix(in_srgb,var(--tier-color)_34%,rgba(215,227,244,0.1))] border-l-[color:var(--tier-color)] bg-azul-painel p-6 sm:grid-cols-[190px_1fr] sm:gap-7 sm:p-[30px]"
    >
        <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[color:var(--tier-color)] opacity-[0.03]"
            style={patternMask(96)}
        />
        <strong className="relative z-10 self-center font-montserrat text-sm font-bold uppercase tracking-[0.08em] text-[color:var(--tier-color)]">
            {name}
        </strong>
        <div className="relative z-10">
            <h3 className="font-poppins text-xl font-bold leading-[1.06] tracking-tight text-branco">{title}</h3>
            <ul className="mt-3 columns-1 list-disc pl-5 text-cinza-texto sm:columns-2">
                {items.map((item) => (
                    <li key={item}>{item}</li>
                ))}
            </ul>
        </div>
    </article>
);

const LogoPlaceholder = ({ name }: { name: string }) => (
    <div className="relative grid min-h-[112px] place-items-center overflow-hidden rounded-[2px] border border-dashed border-acento-principal/40 bg-azul-painel bg-[linear-gradient(145deg,rgba(26,178,255,0.12),transparent_58%)] p-[22px] text-center font-montserrat text-[13px] font-bold leading-[1.35] tracking-[0.02em] text-azul-gelo">
        <span
            aria-hidden="true"
            className="absolute -right-[19px] -top-[19px] h-9 w-9 rotate-45 border border-acento-principal opacity-50"
        />
        {name}
    </div>
);


export default function Parcerias() {
    return (
        <main>
            <PageHeader backgroundImage={faroOldTown} className="pt-[220px] pb-[160px]">
                <SectionHeading
                    title="Contacta com as melhores empresas de tecnologia."
                    eyebrow={<EyeBrow text="PARCERIAS" />}
                    lead="Uma plataforma nacional para aproximar talento, conhecimento e organizações que estão a construir o futuro."
                    className="max-w-[800px]"
                    classNameTitle="mt-1 font-extrabold text-3xl sm:text-4xl lg:text-7xl leading-[1.08] tracking-tight text-branco"
                />
                <div className="flex flex-wrap items-center gap-4 pt-4">
                    <a href="#contacto">
                        <PrimaryButton text="Tornar-me parceiro" />
                    </a>
                    <a href="#niveis">
                        <SecundaryButton text="Ver níveis" />
                    </a>
                </div>
            </PageHeader>

            {/* VALOR */}
            <section className="azulejo-bg bg-azul-superficie py-24">
                <SectionHeading
                    align="center"
                    eyebrow={centerEyebrow('VALOR')}
                    title="Porquê ser parceiro do ENEI 2027?"
                    classNameTitle={h2Center}
                />
                <div className="mx-auto max-w-6xl">
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                        {partnershipBenefits.map((benefit) => (
                            <Tile
                                key={benefit.title}
                                tone={benefit.tone}
                                pattern={true}
                                className="min-h-[240px] p-5"
                            >
                                <IconBox tone={benefit.tone}>{benefit.icon}</IconBox>
                                <h3 className="mb-3 mt-6 font-poppins text-xl font-bold text-white">{benefit.title}</h3>
                                <p className="text-base leading-relaxed text-slate-400">{benefit.text}</p>
                            </Tile>
                        ))}
                    </div>
                </div>
            </section>

            {/* NÍVEIS DE PARCERIA */}
            <section id="niveis" className={`scroll-mt-24 bg-azul-base ${sectionY}`}>
                <div className={wrap}>
                    <SectionHeading
                        align="center"
                        eyebrow={centerEyebrow('PATROCÍNIO')}
                        title="Níveis de parceria"
                        classNameTitle={h2Center}
                        lead="Escolhe o nível de presença que melhor acompanha os objetivos da tua organização."
                    />
                    <div className="mt-[46px] flex flex-col gap-3.5">
                        {tiers.map((tier) => (
                            <TierCard key={tier.name} {...tier} />
                        ))}
                    </div>
                </div>
            </section>

            {/* REDE DE APOIO */}
            <section className={`azulejo-bg bg-azul-superficie ${sectionY}`}>
                <div className={wrap}>
                    <SectionHeading
                        align="center"
                        eyebrow={centerEyebrow('REDE DE APOIO')}
                        title="Uma rede que apoia o ENEI"
                        classNameTitle={h2Center}
                        lead="Instituições académicas, autarquias e organizações tecnológicas unidas à comunidade ENEI."
                    />
                    <div className="mt-10 grid grid-cols-2 gap-3 lg:grid-cols-5">
                        {supporters.map((name) => (
                            <LogoPlaceholder key={name} name={name} />
                        ))}
                    </div>
                </div>
            </section>

            {/* CONTACTO / CTA */}
            <section id="contacto" className={`scroll-mt-24 bg-azul-base ${sectionY}`}>
                <div className={wrap}>
                    <div className="relative overflow-hidden rounded-3xl bg-[linear-gradient(125deg,#006FA6,#00AAFF_58%,#00C5FF)] px-6 py-[34px] text-center text-branco sm:p-[clamp(44px,7vw,80px)]">
                        <span
                            aria-hidden="true"
                            className="pointer-events-none absolute inset-0 bg-white opacity-[0.075]"
                            style={patternMask(140, 'left top')}
                        />
                        <div className="relative z-10">
                            <h2 className="font-poppins text-3xl font-extrabold leading-[1.06] tracking-tight sm:text-4xl lg:text-5xl">
                                Torna-te parceiro do ENEI 2027.
                            </h2>
                            <p className="mx-auto mt-5 max-w-[650px] text-[clamp(17px,2vw,20px)] text-branco/85">
                                Solicita o dossier comercial e conversa com a equipa de parcerias.
                            </p>
                            <div className="mt-[30px] flex justify-center">
                                <a href="mailto:parcerias@enei.pt" className={btnCtaDark}>
                                    Contactar parcerias
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    );
}