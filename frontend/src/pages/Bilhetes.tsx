import type { CSSProperties, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import Eyebrow from '../components/EyeBrow';
import SectionHeading from '../components/SectionHeading';
import azulejoPattern from '../assets/azulejo-pattern-transparent.webp';


interface Ticket {
    category: string;
    title: string;
    price: string;
    features: string[];
    featured?: boolean;
}

interface Step {
    label: string;
    title: string;
    text: string;
}

interface ChecklistColumn {
    title: string;
    items: string[];
}


const tickets: Ticket[] = [
    {
        category: 'ESTUDANTE',
        title: 'Apenas acesso',
        price: 'Acesso',
        features: ['Entrada no evento', 'Programa geral', 'Sem refeições ou estadia'],
    },
    {
        category: 'ESTUDANTE',
        title: 'Acesso + refeições',
        price: 'Acesso + refeições',
        features: ['Entrada no evento', 'Refeições incluídas', 'Sem estadia'],
    },
    {
        category: 'ESTUDANTE',
        title: 'Experiência completa',
        price: 'Experiência completa',
        features: ['Entrada no evento', 'Refeições incluídas', 'Alojamento coletivo'],
        featured: true,
    },
    {
        category: 'NÃO ESTUDANTE',
        title: 'Passe geral',
        price: 'Passe geral',
        features: ['Acesso ao programa', 'Programa completo', 'Condições dedicadas'],
    },
];

const checklist: ChecklistColumn[] = [
    { title: 'Dados pessoais', items: ['Nome completo', 'Email', 'Contacto'] },
    { title: 'Participação', items: ['Instituição', 'Curso', 'Necessidades alimentares'] },
];

const steps: Step[] = [
    { label: 'PASSO 01', title: 'Compara', text: 'Consulta as modalidades e escolhe a experiência certa.' },
    { label: 'PASSO 02', title: 'Compra', text: 'Preenche os teus dados e seleciona as opções da participação.' },
    { label: 'PASSO 03', title: 'Acompanha', text: 'Gere o bilhete e a informação do participante na tua conta.' },
];


const wrap = 'mx-auto w-[calc(100%-28px)] max-w-[1180px] min-[621px]:w-[calc(100%-40px)]';
const sectionY = 'py-[clamp(72px,9vw,124px)]';

const h2Class = 'text-[clamp(30px,4vw,52px)] leading-[1.06] tracking-[-0.045em] text-branco';
const h3Class = 'font-poppins text-xl font-bold leading-[1.06] tracking-[-0.045em] text-branco';
const leadClass = '!text-[clamp(17px,2vw,20px)] text-cinza-texto';

const btn =
    'inline-flex min-h-[46px] items-center justify-center gap-2 rounded-full border px-6 text-sm font-bold transition duration-200 hover:-translate-y-0.5';
const btnPrimary = `${btn} border-transparent bg-acento-principal text-texto-sobre-ciano hover:bg-acento-forte`;
const btnSecondary = `${btn} border-white/25 bg-white/5 text-branco hover:border-white/55`;

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

const gridLines: CSSProperties = {
    backgroundImage:
        'linear-gradient(rgba(26,178,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(26,178,255,0.035) 1px, transparent 1px)',
    backgroundSize: '64px 64px',
    WebkitMaskImage: 'linear-gradient(90deg, transparent, #000 45%, transparent)',
    maskImage: 'linear-gradient(90deg, transparent, #000 45%, transparent)',
};


interface SectionProps {
    id?: string;
    surface?: boolean; 
    contentClassName?: string;
    children: ReactNode;
}

const Section = ({ id, surface = false, contentClassName = '', children }: SectionProps) => (
    <section
        id={id}
        className={`relative scroll-mt-24 overflow-hidden ${sectionY} ${surface ? 'bg-azul-superficie' : 'bg-azul-base'}`}
    >
        {surface && (
            <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 bg-acento-principal opacity-[0.026]"
                style={patternMask(96, 'left top')}
            />
        )}
        <div className={`${wrap} relative z-10 ${contentClassName}`}>{children}</div>
    </section>
);

const CheckList = ({ items }: { items: string[] }) => (
    <ul className="my-5 grid gap-[9px] text-cinza-texto">
        {items.map((item) => (
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
);

const TicketCard = ({ category, title, price, features, featured = false }: Ticket) => (
    <article
        className={`relative flex flex-col overflow-hidden rounded-b-[18px] border border-t-[5px] bg-azul-painel px-[26px] py-[30px] min-[621px]:min-h-[390px] min-[701px]:min-h-[430px] ${featured
                ? 'border-[rgba(229,191,120,0.38)] border-t-areia bg-[linear-gradient(160deg,rgba(229,191,120,0.11),transparent_52%)] shadow-[0_22px_48px_rgba(229,191,120,0.1)]'
                : 'border-gelo/10 border-t-acento-principal'
            }`}
    >
        {/* Padrão azulejo (1,8%) */}
        <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-acento-principal opacity-[0.018]"
            style={patternMask(96)}
        />

        {featured && (
            <span className="absolute right-[18px] top-[18px] z-20 rounded-full border border-[rgba(229,191,120,0.58)] bg-[rgba(229,191,120,0.12)] px-2.5 py-1.5 font-montserrat text-[9px] font-bold uppercase leading-none tracking-[0.1em] text-areia-clara">
                Recomendado
            </span>
        )}

        <div className="relative z-10 flex flex-1 flex-col">
            <p className="m-0 mb-3.5 font-montserrat text-[11px] font-bold uppercase leading-[1.4] tracking-[0.16em] text-acento-forte">
                {category}
            </p>
            <h3 className={`${h3Class} min-[621px]:min-h-[2.15em]`}>{title}</h3>
            <div className="my-[18px] font-poppins text-[34px] font-bold leading-[normal] text-acento-forte min-[621px]:flex min-[621px]:min-h-[3.05em] min-[621px]:items-start">
                {price}
            </div>

            <div className="flex-1">
                <CheckList items={features} />
            </div>

            <button type="button" className={`${btnSecondary} mt-auto w-full cursor-pointer`}>
                Escolher bilhete
            </button>
        </div>
    </article>
);


export default function Bilhetes() {
    return (
        <main className="leading-[1.65]">
            {/* HERO */}
            <header className="relative grid min-h-[560px] items-center overflow-hidden border-b border-gelo/10 bg-azul-base bg-[radial-gradient(circle_at_78%_12%,rgba(26,178,255,0.2),transparent_36%)] pb-[clamp(70px,8vw,110px)] pt-[calc(64px+clamp(84px,10vw,140px))] md:pt-[calc(76px+clamp(84px,10vw,140px))]">
                <span aria-hidden="true" className="pointer-events-none absolute inset-0" style={gridLines} />

                <div className={`${wrap} relative z-10`}>
                    <div className="relative pl-6 min-[621px]:pl-[clamp(24px,6vw,82px)]">
                        <span
                            aria-hidden="true"
                            className="absolute inset-y-0 left-0 w-[5px] rounded-full bg-acento-principal shadow-[0_0_34px_rgba(26,178,255,0.45)] min-[621px]:w-2"
                        />
                        <SectionHeading
                            eyebrow={<Eyebrow text="BILHETES" />}
                            title="Garante o teu lugar no ENEI 2027."
                            lead="Escolhe a modalidade certa e prepara tudo o que precisas para viver o ENEI 2027."
                            className="mb-0 max-w-[900px]"
                            classNameTitle="text-[clamp(38px,6vw,68px)] leading-[1.06] tracking-[-0.045em] text-branco"
                            classNameLead={leadClass}
                        />
                        <div className="mt-[30px] flex flex-wrap gap-3">
                            <a href="#tipos" className={btnSecondary}>Ver modalidades</a>
                            <a href="#tipos" className={btnPrimary}>Comprar bilhete</a>
                        </div>
                    </div>
                </div>
            </header>

            {/* MODALIDADES */}
            <Section id="tipos" surface>
                <SectionHeading
                    eyebrow={<Eyebrow text="MODALIDADES" />}
                    title="Escolhe a experiência certa."
                    lead="Quatro formas de participar, desde o acesso ao programa até à experiência completa."
                    className="mb-[42px]"
                    classNameTitle={h2Class}
                    classNameLead={leadClass}
                />
                <div className="min-[701px]:relative min-[701px]:left-1/2 min-[701px]:w-[min(1440px,calc(100vw-40px))] min-[701px]:-translate-x-1/2">
                    <div className="grid auto-rows-fr grid-cols-1 items-stretch gap-[18px] min-[621px]:grid-cols-2 min-[701px]:grid-cols-4">
                        {tickets.map((ticket) => (
                            <TicketCard key={ticket.title} {...ticket} />
                        ))}
                    </div>
                </div>
            </Section>

            {/* INSCRIÇÃO */}
            <Section>
                <SectionHeading
                    eyebrow={<Eyebrow text="INSCRIÇÃO" />}
                    title="Prepara a tua inscrição"
                    lead="Tem estes elementos contigo para completar o processo de forma simples."
                    className="mb-[38px]"
                    classNameTitle={h2Class}
                    classNameLead={leadClass}
                />
                <div className="grid grid-cols-1 divide-y divide-gelo/10 border-y border-acento-principal/[0.42] min-[621px]:grid-cols-3 min-[621px]:divide-x min-[621px]:divide-y-0">
                    {checklist.map(({ title, items }) => (
                        <article key={title} className="min-w-0 p-7">
                            <h3 className={h3Class}>{title}</h3>
                            <CheckList items={items} />
                        </article>
                    ))}
                    <article className="min-w-0 bg-acento-principal/5 p-7">
                        <h3 className={h3Class}>Canal oficial</h3>
                        <p className="mt-2.5 text-sm text-cinza-texto">
                            Usa apenas a área pessoal do ENEI para enviar dados e acompanhar o bilhete.
                        </p>
                    </article>
                </div>
            </Section>

            {/* PROCESSO */}
            <Section
                surface
                contentClassName="grid grid-cols-1 items-center gap-[clamp(40px,8vw,100px)] min-[701px]:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]"
            >
                <SectionHeading
                    eyebrow={<Eyebrow text="PROCESSO" />}
                    title="Um processo simples"
                    lead="Do primeiro passo à chegada ao evento, tudo fica organizado na tua conta."
                    className="mb-0"
                    classNameTitle={h2Class}
                    classNameLead={leadClass}
                />

                <div className="relative grid gap-6">
                    <span
                        aria-hidden="true"
                        className="absolute bottom-2.5 left-[17px] top-2.5 w-px -translate-x-1/2 bg-acento-principal/[0.42]"
                    />
                    {steps.map(({ label, title, text }) => (
                        <div key={label} className="relative pl-[54px]">
                            <span
                                aria-hidden="true"
                                className="absolute left-[17px] top-1 box-border h-5 w-5 -translate-x-1/2 rounded-full border-[3px] border-azul-base bg-acento-principal shadow-[0_0_0_1px_#1AB2FF]"
                            />
                            <small className="font-montserrat font-bold tracking-[0.08em] text-acento-forte">{label}</small>
                            <h3 className={h3Class}>{title}</h3>
                            <p className="mt-1.5 text-cinza-texto">{text}</p>
                        </div>
                    ))}
                </div>
            </Section>

            {/* AJUDA */}
            <Section surface={false}>
                <SectionHeading
                    align="center"
                    title="Precisas de ajuda?"
                    lead="Consulta as respostas sobre modalidades, alojamento, transportes e participação."
                    className="mb-0"
                    classNameTitle={h2Class}
                    classNameLead={leadClass}
                />
                <div className="mt-[30px] flex justify-center">
                    <Link to="/informacao-ajuda" className={btnPrimary}>
                        Informação &amp; Ajuda
                    </Link>
                </div>
            </Section>
        </main>
    );
}