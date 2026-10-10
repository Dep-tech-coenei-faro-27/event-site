import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import SectionHeading from '../components/SectionHeading';
import EyeBrow from '../components/EyeBrow';
import faroBaixa from '../assets/faro-aerial.webp';
import faroBaixaPhoto from '../assets/faro-baixa.webp';
import gambelasImage from '../assets/gambelas.webp';
import companiesImage from '../assets/about-companies.webp';
import talksImage from '../assets/about-talks.webp';
import workshopImage from '../assets/about-workshop.webp';
import Tile, { IconBox } from '../components/Tile';
import type { Tone } from '../components/Tones';
import { usePageMeta } from "../utils/usePageMeta";


interface TileItem {
    title: string;
    text: string;
    tone: Tone;
    icon: ReactNode;
}

interface Fact {
    value: string;
    label: string;
}

interface Project {
    title: string;
    text: string;
}

const facts: Fact[] = [
    { value: '18.ª', label: 'Edição nacional realizada em Faro.' },
    { value: '4 dias', label: 'Conhecimento, networking e comunidade.' },
    { value: '≈10 mil', label: 'Estudantes na Universidade do Algarve.' },
    { value: '300+', label: 'Dias de sol por ano na região.' },
];

const pillars: TileItem[] = [
    {
        title: 'Conhecimento',
        tone: 'teal',
        text: 'Aprender com especialistas, experimentar novas ferramentas e descobrir caminhos profissionais.',
        icon: (<><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5z" /><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5z" /></>),
    },
    {
        title: 'Networking',
        tone: 'periwinkle',
        text: 'Criar relações genuínas entre estudantes, comunidades, academia e indústria.',
        icon: (<><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2.5" /><path d="M3.5 20a5.5 5.5 0 0 1 11 0M14 15.5a4.5 4.5 0 0 1 6.5 4" /></>),
    },
    {
        title: 'Cidadania',
        tone: 'teal',
        text: 'Construir uma comunidade tecnológica mais responsável, diversa e participativa.',
        icon: (<><path d="M12 3 5 6v5c0 4.7 2.9 8.1 7 10 4.1-1.9 7-5.3 7-10V6z" /><path d="m9 12 2 2 4-4" /></>),
    },
];

const departments: TileItem[] = [
    {
        title: 'Coordenação', text: 'Estratégia e articulação geral.', tone: 'periwinkle',
        icon: (<><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2 5-5 2 2-5z" /></>),
    },
    {
        title: 'Programa', text: 'Conteúdos e experiências.', tone: 'sand',
        icon: (<><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M8 3v4M16 3v4M3 10h18M8 14h3M8 17h6" /></>),
    },
    {
        title: 'Operações', text: 'Logística e produção.', tone: 'teal',
        icon: <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9" />,
    },
    {
        title: 'Comunicação', text: 'Marca e comunidade.', tone: 'coral',
        icon: (<><path d="M3 11v2a2 2 0 0 0 2 2h2l2 5h3l-2-5 9 3V6L7 9H5a2 2 0 0 0-2 2z" /><path d="M19 9a3 3 0 0 1 0 6" /></>),
    },
];

const faroFeatures: string[] = [
    'Universidade do Algarve e comunidade académica internacional',
    'Algarve Tech Hub, startups e empresas tecnológicas',
    'Acessos ferroviários, rodoviários e aéreos',
    'Cidade compacta, património e natureza',
];

const projects: Project[] = [
    {
        title: 'Algarve Summit',
        text: 'Palestras, workshops e painéis que ligam academia, investigação e empresas da região.',
    },
    {
        title: 'GDG Buildathon',
        text: 'Maratona de desenvolvimento orientada à colaboração, pensamento crítico e criação tecnológica.',
    },
];


const wrap = 'mx-auto w-[calc(100%-40px)] max-w-[1180px]';
const sectionY = 'py-[clamp(72px,9vw,124px)]';
const h2Class = 'mt-1 font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-[1.08] tracking-tight text-branco';

const btn =
    'inline-flex min-h-[46px] items-center justify-center rounded-full border px-6 text-sm font-bold transition duration-200 hover:-translate-y-0.5';
const btnPrimary = `${btn} border-transparent bg-acento-principal text-texto-sobre-ciano hover:bg-acento-forte`;
const btnCtaDark = `${btn} border-white/15 bg-azul-painel text-branco hover:bg-azul-elevado`;
const btnCtaSecondary = `${btn} border-white/70 bg-[rgba(3,16,31,0.72)] text-branco shadow-[0_8px_22px_rgba(0,0,0,0.18)] hover:border-white hover:bg-[rgba(3,16,31,0.9)]`;

const galleryImages = [
    { src: talksImage, alt: 'Palestra num auditório do ENEI', className: 'col-span-2 sm:col-span-1 sm:row-span-2' },
    { src: workshopImage, alt: 'Participantes num workshop técnico', className: '' },
    { src: companiesImage, alt: 'Área de empresas e networking', className: '' },
];

const historyItems = [
    { label: 'Origem', title: 'Uma comunidade nacional', text: 'Estudantes de informática juntam-se para trocar conhecimento e experiências.' },
    { label: 'Evolução', title: 'Mais formatos, mais ligações', text: 'O encontro cresce com workshops, palestras, desafios e contacto empresarial.' },
    { label: '2027', title: 'O ENEI chega a Faro', text: 'Uma nova edição, preparada pela comunidade académica do Algarve.' },
];

export default function Sobre() {

    usePageMeta( "Sobre · ENEI 2027", "Conhece o ENEI, o Encontro Nacional de Estudantes de Informática, que decorre em Faro, no Algarve, de 1 a 4 de abril de 2027.",);

    return (
        <main>
            <PageHeader backgroundImage={faroBaixa} className="pt-[220px] pb-[160px]">
                <SectionHeading
                    title="O que é o ENEI?"
                    eyebrow={<EyeBrow text="SOBRE" />}
                    lead="O Encontro Nacional de Estudantes de Informática reúne estudantes, comunidades, instituições e empresas numa experiência criada para aprender, partilhar e construir ligações."
                    className="max-w-[800px] text-branco"
                    classNameTitle="mt-1 font-extrabold text-3xl sm:text-4xl lg:text-7xl leading-[1.08] tracking-tight text-branco"
                />
            </PageHeader>

            {/* GALERIA */}
            <section className="azulejo-bg bg-azul-superficie py-12">
                <div className={`${wrap} grid grid-cols-2 grid-rows-[240px_150px] gap-3.5 sm:-translate-y-7 sm:grid-cols-[1.35fr_0.65fr] sm:grid-rows-[220px_220px]`}>
                    {galleryImages.map(({ src, alt, className }) => (
                        <figure
                            key={alt}
                            className={`group m-0 overflow-hidden rounded-[28px] border border-gelo/10 bg-azul-painel ${className}`}
                        >
                            <img
                                src={src}
                                alt={alt}
                                className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.025]"
                            />
                        </figure>
                    ))}
                </div>
            </section>

            {/* HISTÓRIA */}
            <section className={`${wrap} py-14`}>
                <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-8">
                    <div>
                        <SectionHeading
                            title="Uma história de inovação."
                            eyebrow={<EyeBrow text="HISTÓRIA" />}
                            className="max-w-[800px] text-branco"
                            lead="Uma iniciativa estudantil que atravessa gerações e continua a aproximar o ensino superior do ecossistema tecnológico nacional."
                            classNameTitle="mt-1 font-extrabold text-3xl sm:text-4xl lg:text-5xl leading-[1.08] tracking-tight text-branco"
                        />
                    </div>

                    <div className="w-full max-w-[540px] lg:ml-auto">
                        <div className="azulejo-bg relative overflow-hidden rounded-bl-[12px] rounded-br-[48px] rounded-tl-[48px] rounded-tr-[12px] border border-[#1e2d4a] bg-azul-superficie p-7 shadow-2xl md:p-8">
                            <div className="azulejo-bg pointer-events-none absolute inset-0 opacity-30" />

                            <div className="relative z-10 ml-3 space-y-7 border-l-[2px] border-[#184673] py-1">
                                {historyItems.map(({ label, title, text }) => (
                                    <div key={label} className="relative pl-7 md:pl-9">
                                        <div className="absolute -left-[11px] top-1 flex h-5 w-5 items-center justify-center rounded-full border-[2px] border-cyan-400 bg-azul-base ring-[3px] ring-azul-base">
                                            <div className="h-[8px] w-[8px] rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
                                        </div>
                                        <small className="mb-1 block text-[11px] font-bold uppercase tracking-[0.15em] text-cyan-400">
                                            {label}
                                        </small>
                                        <h3 className="mb-1.5 font-poppins text-lg font-bold leading-tight tracking-tight text-white md:text-[22px]">
                                            {title}
                                        </h3>
                                        <p className="text-[15px] leading-relaxed text-slate-300">{text}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* CONTEXTO */}
            <section className={`bg-azul-superficie ${sectionY}`}>
                <div className={wrap}>
                    <SectionHeading
                        title="Academia, região e tecnologia."
                        eyebrow={<EyeBrow text="CONTEXTO" />}
                        className="max-w-[800px] text-branco"
                        classNameTitle={h2Class}
                    />
                    <div className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-bl-[28px] rounded-tr-[28px] border border-gelo/10 bg-gelo/10 lg:grid-cols-4">
                        {facts.map(({ value, label }) => (
                            <div key={value} className="min-h-[160px] bg-azul-painel p-[26px]">
                                <strong className="block font-poppins text-[clamp(25px,3vw,38px)] font-bold leading-none text-branco">
                                    {value}
                                </strong>
                                <span className="mt-2.5 block text-sm text-cinza-texto">{label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* VALORES */}
            <section className={`bg-azul-base ${sectionY}`}>
                <div className={`${wrap} text-center`}>
                    <EyeBrow text="VALORES" />
                    <h2 className={h2Class}>Os nossos pilares</h2>
                    <div className="mt-[42px] grid grid-cols-1 gap-3.5 text-left md:grid-cols-3">
                        {pillars.map(({ title, text, tone, icon }) => (
                            <Tile rounded showInnerBorder key={title} tone={tone} pattern className="px-6 py-[30px] sm:px-[34px]">
                                <IconBox tone={tone}>{icon}</IconBox>
                                <h3 className="font-poppins text-xl font-bold leading-[1.06] tracking-tight text-branco">{title}</h3>
                                <p className="mt-2.5 text-sm text-cinza-texto">{text}</p>
                            </Tile>
                        ))}
                    </div>
                </div>
            </section>

            {/* FARO */}
            <section id="faro" className={`bg-azul-superficie ${sectionY}`}>
                <div className={`${wrap} grid grid-cols-1 items-center gap-12 lg:grid-cols-[minmax(0,1.08fr)_minmax(300px,0.92fr)] lg:gap-[clamp(40px,8vw,100px)]`}>
                    <div className="aspect-[16/10] overflow-hidden rounded-[22px] border border-acento-principal/30 bg-azul-painel shadow-[0_22px_50px_rgba(0,0,0,0.24)]">
                        <img
                            src={faroBaixaPhoto}
                            alt="Marina e centro histórico de Faro"
                            className="h-full w-full object-cover object-center"
                        />
                    </div>
                    <div>
                        <SectionHeading
                            title="Porquê Faro?"
                            eyebrow={<EyeBrow text="LOCALIZAÇÃO" />}
                            lead="Capital do Algarve, Faro cruza património histórico, a Ria Formosa e um ecossistema tecnológico em crescimento."
                            className="text-branco"
                            classNameTitle={h2Class}
                        />
                        <ul className="my-5 grid gap-[9px] text-cinza-texto">
                            {faroFeatures.map((item) => (
                                <li key={item} className="relative pl-7">
                                    <svg
                                        viewBox="0 0 24 24"
                                        aria-hidden="true"
                                        className="absolute left-0 top-[0.26em] h-[17px] w-[17px] fill-none stroke-acento-principal stroke-[2.25] [stroke-linecap:round] [stroke-linejoin:round]"
                                    >
                                        <path d="m5 12 4 4L19 6" />
                                    </svg>
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </section>

            {/* UALG + NEEI */}
            <section className={`bg-azul-base ${sectionY}`}>
                <div className={`${wrap} grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-[clamp(40px,8vw,100px)]`}>
                    <div>
                        <SectionHeading
                            title="Uma comunidade que transforma teoria em prática."
                            eyebrow={<EyeBrow text="UALG + NEEI" />}
                            lead="O NEEI aproxima estudantes do tecido empresarial através de atividades, voluntariado e participação ativa no ecossistema tecnológico algarvio."
                            className="text-branco"
                            classNameTitle={h2Class}
                        />
                        <div className="mt-8 border-t border-acento-principal/40">
                            {projects.map(({ title, text }) => (
                                <article
                                    key={title}
                                    className="grid gap-2 border-b border-gelo/10 py-[22px] sm:grid-cols-[minmax(150px,0.55fr)_minmax(0,1fr)] sm:gap-7"
                                >
                                    <h3 className="font-poppins text-xl font-bold leading-[1.06] tracking-tight text-branco">{title}</h3>
                                    <p className="text-sm text-cinza-texto">{text}</p>
                                </article>
                            ))}
                        </div>
                    </div>
                    <div className="relative min-h-[340px] self-stretch overflow-hidden rounded-3xl border border-acento-principal/40 shadow-[0_28px_70px_rgba(0,0,0,0.32)] lg:min-h-[360px]">
                        <img
                            src={gambelasImage}
                            alt="Campus das Gambelas da Universidade do Algarve"
                            className="absolute inset-0 h-full w-full object-cover object-center"
                        />
                    </div>
                </div>
            </section>

            {/* ORGANIZAÇÃO */}
            <section className={`bg-azul-superficie ${sectionY}`}>
                <div className={wrap}>
                    <div className="mb-11 flex flex-col gap-4 md:flex-row md:items-end md:justify-between md:gap-[30px]">
                        <SectionHeading
                            title="Quem organiza o ENEI 2027?"
                            eyebrow={<EyeBrow text="ORGANIZAÇÃO" />}
                            className="text-branco"
                            classNameTitle={h2Class}
                        />
                        <p className="max-w-[560px] text-[clamp(17px,2vw,20px)] text-cinza-texto">
                            Uma equipa multidisciplinar de estudantes, apoiada por estruturas académicas e parceiros.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
                        {departments.map(({ title, text, tone, icon }) => (
                            <Tile rounded showInnerBorder key={title} tone={tone} className="px-6 py-7">
                                <IconBox tone={tone}>{icon}</IconBox>
                                <h3 className="font-poppins text-xl font-bold leading-[1.06] tracking-tight text-branco">{title}</h3>
                                <p className="mt-2.5 text-sm text-cinza-texto">{text}</p>
                            </Tile>
                        ))}
                    </div>
                    <div className="mt-[30px] flex justify-center">
                        <Link to="/equipa" className={btnPrimary}>Conhecer a equipa</Link>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className={`bg-azul-base ${sectionY}`}>
                <div className={wrap}>
                    <div className="relative overflow-hidden rounded-3xl bg-[linear-gradient(125deg,#006FA6,#00AAFF_58%,#00C5FF)] p-[clamp(24px,7vw,80px)] text-branco">
                        <div className="relative z-10">
                            <h2 className="font-poppins text-3xl font-extrabold leading-[1.06] tracking-tight sm:text-4xl lg:text-5xl">
                                Fica a par de tudo.
                            </h2>
                            <p className="mt-5 max-w-[650px] text-[clamp(17px,2vw,20px)] text-branco/85">
                                Consulta a agenda, prepara a tua visita e acompanha as inscrições.
                            </p>
                            <div className="mt-[30px] flex flex-wrap gap-3">
                                <Link to="/agenda" className={btnCtaDark}>Explorar agenda</Link>
                                <Link to="/bilhetes" className={btnCtaSecondary}>Comprar bilhete</Link>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    );
}