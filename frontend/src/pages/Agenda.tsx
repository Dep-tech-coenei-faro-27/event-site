import { useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import Eyebrow from '../components/EyeBrow';
import PageHeader from '../components/PageHeader';
import SectionHeading from '../components/SectionHeading';
import Tile, { IconBox } from '../components/Tile';
import type { Tone } from '../components/Tones';
import agendaAuditorio from '../assets/agenda-auditorio.webp';
import portraitPlaceholder from '../assets/portrait-placeholder.svg';
import azulejoPattern from '../assets/azulejo-pattern-transparent.webp';



type DayId = 'quinta' | 'sexta' | 'sabado' | 'domingo';

interface ScheduleItem {
    time: string;
    title: string;
    tag: string;
    tone: Tone;
}

interface Day {
    id: DayId;
    tab: string; // "Quinta"
    date: string; // "1 Abr"
    iso: string; // "2027-04-01"
    label: string; // "Quinta-feira · 1 abril"
    items: ScheduleItem[];
}

interface Speaker {
    track: string;
    title: string;
    role: string;
    session: string;
    when: string;
    alt: string;
    tone: Tone;
}

interface Axis {
    title: string;
    number?: string;
    icon?: ReactNode;
    items: string[];
}

interface IconItem {
    title: string;
    text: string;
    tone: Tone;
    icon: ReactNode;
}



// Sexta e sábado partilham a mesma estrutura; só mudam os números dos workshops.
const fullDay = (firstWorkshops: string, secondWorkshops: string): ScheduleItem[] => [
    { time: '10:00', title: `Palestra e workshops ${firstWorkshops}`, tag: 'Palestra / workshop', tone: 'coral' },
    { time: '11:00', title: 'Palestra', tag: 'Palestra', tone: 'cyan' },
    { time: '12:00', title: 'Almoço', tag: 'Refeição', tone: 'teal' },
    { time: '14:00', title: `Palestra e workshops ${secondWorkshops}`, tag: 'Palestra / workshop', tone: 'coral' },
    { time: '15:00', title: 'Palestra', tag: 'Palestra', tone: 'cyan' },
    { time: '16:30', title: 'Coffee break', tag: 'Networking', tone: 'sand' },
    { time: '17:00', title: 'Palestra', tag: 'Palestra', tone: 'cyan' },
    { time: '18:00', title: 'Tertúlia', tag: 'Tertúlia', tone: 'periwinkle' },
    { time: '20:00', title: 'Jantar', tag: 'Refeição', tone: 'teal' },
    { time: '22:00', title: 'Atividades noturnas', tag: 'Noite', tone: 'periwinkle' },
];

const days: Day[] = [
    {
        id: 'quinta',
        tab: 'Quinta',
        date: '1 Abr',
        iso: '2027-04-01',
        label: 'Quinta-feira · 1 abril',
        items: [
            { time: '14:00', title: 'Check-ins', tag: 'Check-in', tone: 'sand' },
            { time: '18:00', title: 'Sessão de boas-vindas', tag: 'Boas-vindas', tone: 'cyan' },
            { time: '20:00', title: 'Jantar e arraial académico', tag: 'Jantar', tone: 'teal' },
        ],
    },
    {
        id: 'sexta',
        tab: 'Sexta',
        date: '2 Abr',
        iso: '2027-04-02',
        label: 'Sexta-feira · 2 abril',
        items: fullDay('#1, #2 e #3', '#4, #5 e #6'),
    },
    {
        id: 'sabado',
        tab: 'Sábado',
        date: '3 Abr',
        iso: '2027-04-03',
        label: 'Sábado · 3 abril',
        items: fullDay('#10, #11 e #12', '#13, #14 e #15'),
    },
    {
        id: 'domingo',
        tab: 'Domingo',
        date: '4 Abr',
        iso: '2027-04-04',
        label: 'Domingo · 4 abril',
        items: [
            { time: '10:00', title: 'Nascer do sol na praia', tag: 'Social', tone: 'sand' },
            { time: '12:00', title: 'Almoço', tag: 'Refeição', tone: 'teal' },
            { time: '14:00', title: 'Tertúlia', tag: 'Tertúlia', tone: 'periwinkle' },
            { time: '16:00', title: 'Sessão de encerramento', tag: 'Encerramento', tone: 'cyan' },
        ],
    },
];

const speakers: Speaker[] = [
    {
        track: 'Keynote',
        title: 'Orador principal',
        role: 'Nome · Organização',
        session: 'Tema a anunciar',
        when: 'Data a confirmar',
        alt: 'Retrato do orador principal ainda por anunciar',
        tone: 'cyan',
    },
    {
        track: 'Tecnologia',
        title: 'Especialista convidado',
        role: 'Nome · Organização',
        session: 'Palestra técnica',
        when: 'Data a confirmar',
        alt: 'Retrato de especialista convidado ainda por anunciar',
        tone: 'teal',
    },
    {
        track: 'Indústria',
        title: 'Representante da indústria',
        role: 'Nome · Organização',
        session: 'Experiência e carreira',
        when: 'Data a confirmar',
        alt: 'Retrato de representante da indústria ainda por anunciar',
        tone: 'sand',
    },
    {
        track: 'Comunidade',
        title: 'Convidado da comunidade',
        role: 'Nome · Organização',
        session: 'Conversa aberta',
        when: 'Data a confirmar',
        alt: 'Retrato de convidado da comunidade ainda por anunciar',
        tone: 'periwinkle',
    },
];

const axes: Axis[] = [
    { number: '01', title: 'Competições', items: ['Capture the Flag', 'Programação competitiva', 'Desafios de convívio'] },
    { number: '02', title: 'Pedagógico', items: ['Palestras', 'Workshops', 'Networking empresarial'] },
    { number: '03', title: 'Recreativo', items: ['Cultura académica', 'Descoberta de Faro', 'Bem-estar e comunidade'] },
    {
        title: 'Gamificação',
        items: ['Badges', 'Moedas virtuais', 'Recompensas'],
        icon: (
            <>
                <path d="M8 4h8v4a4 4 0 0 1-8 0z" />
                <path d="M8 6H4v2a4 4 0 0 0 4 4M16 6h4v2a4 4 0 0 1-4 4M12 12v5M9 17h6M8 21h8" />
            </>
        ),
    },
];

const experiences: IconItem[] = [
    {
        title: 'Capture the Flag',
        text: 'Desafios técnicos de cibersegurança e hacking ético.',
        tone: 'coral',
        icon: (
            <>
                <path d="M5 21V4M5 5h11l-2 4 2 4H5" />
                <path d="m8.5 9.5 1.5 1.5 3-3" />
            </>
        ),
    },
    {
        title: 'Programação competitiva',
        text: 'Raciocínio, lógica e rapidez na resolução de problemas algorítmicos.',
        tone: 'cyan',
        icon: <path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14" />,
    },
    {
        title: 'Arraial académico',
        text: 'Integração com a comunidade académica da Universidade do Algarve.',
        tone: 'sand',
        icon: (
            <>
                <path d="M4 5h16M5 5l2 6 3-6 3 6 3-6 3 6" />
                <path d="M6 15v5M18 15v5M4 20h16" />
            </>
        ),
    },
    {
        title: 'Dr. Why',
        text: 'Quiz interativo de cultura geral e competição amigável.',
        tone: 'periwinkle',
        icon: (
            <>
                <circle cx="12" cy="12" r="9" />
                <path d="M9.8 9a2.4 2.4 0 1 1 3.7 2c-1 .6-1.5 1.1-1.5 2.5M12 17.5h.01" />
            </>
        ),
    },
    {
        title: 'Jantar empresarial',
        text: 'Networking direto e informal entre participantes e parceiros.',
        tone: 'coral',
        icon: (
            <path d="M6 3v8M3.5 3v5A2.5 2.5 0 0 0 6 10.5 2.5 2.5 0 0 0 8.5 8V3M6 10.5V21M16 3v18M16 3c3 2 4 5 4 8h-4" />
        ),
    },
    {
        title: 'Passeio na praia',
        text: 'Um momento de bem-estar e comunidade junto à costa algarvia.',
        tone: 'teal',
        icon: (
            <>
                <circle cx="12" cy="8" r="3" />
                <path d="M12 2v2M12 12v2M6 8H4M20 8h-2M7.8 3.8 6.4 2.4M17.6 13.6l-1.4-1.4M16.2 3.8l1.4-1.4M6.4 13.6l1.4-1.4M3 19c2-2 4-2 6 0s4 2 6 0 4-2 6 0" />
            </>
        ),
    },
];

const platformItems: IconItem[] = [
    {
        title: 'Badges',
        text: 'Conquistas associadas à participação e exploração.',
        tone: 'sand',
        icon: (
            <>
                <circle cx="12" cy="9" r="6" />
                <path d="m8.5 14-1 7 4.5-2 4.5 2-1-7M9.5 9l1.5 1.5 3-3" />
            </>
        ),
    },
    {
        title: 'Progressão',
        text: 'Moedas virtuais e recompensas por envolvimento.',
        tone: 'teal',
        icon: (
            <>
                <path d="M4 18 10 12l4 4 6-8" />
                <path d="M15 8h5v5" />
            </>
        ),
    },
    {
        title: 'Ativações',
        text: 'Pontos de interação distribuídos pelo evento.',
        tone: 'periwinkle',
        icon: <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2M20 14v2M14 20h2M18 18h2v2" />,
    },
    {
        title: 'Comunidade',
        text: 'Novas formas de ligar participantes, oradores e empresas.',
        tone: 'coral',
        icon: (
            <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8z" />
        ),
    },
];

const wrap = 'mx-auto w-[calc(100%-28px)] max-w-[1180px] min-[621px]:w-[calc(100%-40px)]';
const sectionY = 'py-[clamp(72px,9vw,124px)]';
const scheduleY = 'py-[clamp(72px,8vw,112px)]'; // .agenda-schedule-section

const h2Class = 'text-[clamp(30px,4vw,52px)] leading-[1.06] tracking-[-0.045em] text-branco';
const h3Class = 'font-poppins text-xl font-bold leading-[1.06] tracking-[-0.045em] text-branco';
const leadClass = '!text-[clamp(17px,2vw,20px)] text-cinza-texto';

const accent: Record<Tone, { text: string; borderTop: string; tag: string; badge: string }> = {
    cyan: {
        text: 'text-acento-forte',
        borderTop: 'border-t-acento-forte',
        tag: 'border-acento-forte/[0.44] bg-acento-forte/[0.08] text-acento-forte',
        badge: 'border-acento-forte/[0.52] text-acento-forte',
    },
    teal: {
        text: 'text-verde-agua',
        borderTop: 'border-t-verde-agua',
        tag: 'border-verde-agua/[0.44] bg-verde-agua/[0.08] text-verde-agua',
        badge: 'border-verde-agua/[0.52] text-verde-agua',
    },
    sand: {
        text: 'text-areia',
        borderTop: 'border-t-areia',
        tag: 'border-areia/[0.44] bg-areia/[0.08] text-areia',
        badge: 'border-areia/[0.52] text-areia',
    },
    coral: {
        text: 'text-coral-suave',
        borderTop: 'border-t-coral-suave',
        tag: 'border-coral-suave/[0.44] bg-coral-suave/[0.08] text-coral-suave',
        badge: 'border-coral-suave/[0.52] text-coral-suave',
    },
    periwinkle: {
        text: 'text-pervinca',
        borderTop: 'border-t-pervinca',
        tag: 'border-pervinca/[0.44] bg-pervinca/[0.08] text-pervinca',
        badge: 'border-pervinca/[0.52] text-pervinca',
    },
};

const experienceColors = ['#1AB2FF', '#5BD6C4', '#E5BF78'];

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

/* ---------- Componentes locais ---------- */

interface SectionProps {
    id?: string;
    surface?: boolean; // secções ímpares: fundo "surface" + padrão azulejo (2,6%)
    paddingClass?: string;
    contentClassName?: string;
    children: ReactNode;
}

const Section = ({ id, surface = false, paddingClass = sectionY, contentClassName = '', children }: SectionProps) => (
    <section
        id={id}
        className={`relative scroll-mt-24 overflow-hidden ${paddingClass} ${surface ? 'bg-azul-superficie' : 'bg-azul-base'}`}
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

interface SplitHeadingProps {
    eyebrow: string;
    title: string;
    lead: string;
    className?: string;
}

const SplitHeading = ({ eyebrow, title, lead, className = 'mb-11' }: SplitHeadingProps) => (
    <div className={`block min-[621px]:flex min-[621px]:items-end min-[621px]:justify-between min-[621px]:gap-[30px] ${className}`}>
        <SectionHeading
            eyebrow={<Eyebrow text={eyebrow} />}
            title={title}
            className="mb-0"
            classNameTitle={h2Class}
        />
        <p className="mt-4 max-w-[560px] text-[clamp(17px,2vw,20px)] text-cinza-texto min-[621px]:mt-0">{lead}</p>
    </div>
);

const CheckList = ({ items, className = '' }: { items: string[]; className?: string }) => (
    <ul className={`grid gap-[9px] text-cinza-texto ${className}`}>
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

const ScheduleRow = ({ iso, item }: { iso: string; item: ScheduleItem }) => (
    <article className="grid min-h-[78px] grid-cols-[64px_minmax(0,1fr)] items-center gap-3.5 border-b border-gelo/10 px-0 py-[22px] last:border-b-0 min-[621px]:grid-cols-[110px_minmax(0,1fr)_auto] min-[621px]:gap-6 min-[621px]:px-2">
        <time
            dateTime={`${iso}T${item.time}`}
            className="font-montserrat text-sm font-bold leading-none tabular-nums text-acento-principal min-[621px]:text-lg"
        >
            {item.time}
        </time>
        <div>
            <h3 className="font-poppins text-base font-bold leading-[1.06] tracking-[-0.045em] text-branco min-[621px]:text-lg">
                {item.title}
            </h3>
        </div>
        <span
            className={`hidden rounded-full border px-2.5 py-[5px] font-montserrat text-[10px] font-semibold uppercase min-[621px]:block ${accent[item.tone].tag}`}
        >
            {item.tag}
        </span>
    </article>
);

const SpeakerCard = ({ track, title, role, session, when, alt, tone }: Speaker) => (
    <article
        className={`group min-w-0 overflow-hidden border border-t-4 border-gelo/10 bg-azul-painel ${accent[tone].borderTop}`}
    >
        <figure className="relative m-0 aspect-[4/5] overflow-hidden border-b border-gelo/10 bg-azul-superficie">
            <img
                src={portraitPlaceholder}
                alt={alt}
                width={800}
                height={800}
                loading="lazy"
                className="block h-full w-full object-cover saturate-[0.72] transition duration-[350ms] group-hover:scale-[1.025] group-hover:saturate-[0.9]"
            />
            <span
                className={`absolute right-3.5 top-3.5 rounded-full border bg-[rgba(5,13,33,0.82)] px-[9px] py-1.5 font-montserrat text-[8px] font-bold uppercase leading-none tracking-[0.11em] backdrop-blur-[8px] ${accent[tone].badge}`}
            >
                Por anunciar
            </span>
        </figure>

        <div className="px-[18px] pb-[22px] pt-5">
            <p className={`m-0 mb-2.5 font-montserrat text-[9px] font-bold uppercase leading-none tracking-[0.13em] ${accent[tone].text}`}>
                {track}
            </p>
            <h3 className="m-0 font-poppins text-[19px] font-bold leading-tight tracking-[-0.045em] text-branco min-[621px]:min-h-[2.5em]">
                {title}
            </h3>
            <p className="mt-2 text-[13px] text-cinza-texto">{role}</p>
            <dl className="mt-5 grid gap-3 border-t border-gelo/10 pt-[18px]">
                <div className="min-w-0">
                    <dt className="font-montserrat text-[8px] font-bold uppercase leading-none tracking-[0.12em] text-cinza-subtil">
                        Sessão
                    </dt>
                    <dd className="m-0 mt-1.5 text-xs leading-[1.4] text-branco">{session}</dd>
                </div>
                <div className="min-w-0">
                    <dt className="font-montserrat text-[8px] font-bold uppercase leading-none tracking-[0.12em] text-cinza-subtil">
                        Quando
                    </dt>
                    <dd className="m-0 mt-1.5 text-xs leading-[1.4] text-branco">{when}</dd>
                </div>
            </dl>
        </div>
    </article>
);

const AxisCard = ({ title, number, icon, items, index }: Axis & { index: number }) => {
    // Borda esquerda: todas (exceto a 1.ª) a partir de 621px; a 3.ª só quando há 4 colunas (>700px)
    const leftBorder =
        index === 0
            ? ''
            : index === 2
                ? 'min-[701px]:border-l min-[701px]:border-l-gelo/10'
                : 'min-[621px]:border-l min-[621px]:border-l-gelo/10';

    return (
        <article
            className={`flex min-h-[280px] min-w-0 flex-col border-t-4 border-t-acento-principal px-[26px] py-[30px] ${leftBorder}`}
        >
            {icon ? (
                <span aria-hidden="true" className="flex min-h-[48px] items-center text-acento-forte opacity-[0.68]">
                    <svg
                        viewBox="0 0 24 24"
                        focusable="false"
                        className="block h-[38px] w-[38px] fill-none stroke-current stroke-2 [stroke-linecap:round] [stroke-linejoin:round]"
                    >
                        {icon}
                    </svg>
                </span>
            ) : (
                <span className="flex min-h-[48px] items-center font-montserrat text-[48px] font-extrabold leading-none tracking-[-0.08em] text-acento-forte opacity-[0.68]">
                    {number}
                </span>
            )}
            <h3 className={h3Class}>{title}</h3>
            <CheckList items={items} className="mb-5 mt-auto" />
        </article>
    );
};

const ExperienceCard = ({ title, text, tone, icon, index }: IconItem & { index: number }) => (
    <article
        style={{ '--tile-color': experienceColors[index % 3] } as CSSProperties}
        className="relative flex min-h-[220px] flex-col justify-center overflow-hidden border border-l-4 border-[color:color-mix(in_srgb,var(--tile-color)_38%,rgba(215,227,244,0.1))] border-l-[color:var(--tile-color)] bg-azul-painel p-7 shadow-[inset_0_1px_0_rgba(255,255,255,0.025)]"
    >
        <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[color:var(--tile-color)] opacity-[0.038]"
            style={patternMask(92)}
        />
        <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-4 border border-[color:color-mix(in_srgb,var(--tile-color)_18%,transparent)]"
        />
        <div className="relative z-10">
            <div className="[&>div]:mb-[22px]">
                <IconBox tone={tone}>{icon}</IconBox>
            </div>
            <h3 className={h3Class}>{title}</h3>
            <p className="mt-2.5 text-sm text-cinza-texto">{text}</p>
        </div>
    </article>
);


export default function Agenda() {
    const [activeDay, setActiveDay] = useState<DayId>('quinta');

    return (
        <main className="leading-[1.65]">
            {/* HERO */}
            <PageHeader
                backgroundImage={agendaAuditorio}
                backgroundPosition="center 52%"
                overlay="linear-gradient(90deg, rgba(5,13,33,0.9), rgba(5,13,33,0.68) 50%, rgba(5,13,33,0.84))"
                align="center"
                className="pb-[clamp(70px,8vw,110px)] pt-[calc(64px+clamp(84px,10vw,140px))] md:pt-[calc(76px+clamp(84px,10vw,140px))]"
            >
                <div className="text-center [text-shadow:0_3px_24px_rgba(0,0,0,0.48)]">
                    <SectionHeading
                        align="center"
                        eyebrow={<Eyebrow text="PROGRAMA" />}
                        title="Quatro dias para experimentar."
                        lead="Conhece os eixos, atividades e experiências que dão forma ao ENEI 2027."
                        className="mb-0"
                        classNameTitle="mx-auto max-w-[850px] text-[clamp(42px,7vw,78px)] uppercase leading-[1.06] tracking-[-0.045em] text-branco"
                        classNameLead="!text-[clamp(17px,2vw,20px)] text-white/[0.78]"
                    />
                    <div className="mx-auto mt-[26px] flex w-fit items-center gap-2 rounded-full border border-acento-principal/[0.62] bg-[rgba(5,13,33,0.72)] px-3 py-[7px] font-montserrat text-[11px] font-semibold leading-[1.2] tracking-[0.04em] text-gelo shadow-[0_14px_36px_rgba(0,0,0,0.22)] backdrop-blur-[8px]">
                        1–4 abril 2027 · Campus das Gambelas
                    </div>
                </div>
            </PageHeader>

            {/* AGENDA POR DIA */}
            <Section surface paddingClass={scheduleY}>
                <SplitHeading
                    eyebrow="AGENDA POR DIA"
                    title="Quatro dias, um programa completo."
                    lead="Consulta os principais momentos de cada dia do ENEI 2027."
                />

                <div
                    role="tablist"
                    aria-label="Dias do programa"
                    className="mb-10 grid grid-cols-2 gap-2.5 min-[621px]:mb-[52px] min-[621px]:flex min-[621px]:flex-wrap min-[621px]:justify-center"
                >
                    {days.map(({ id, tab, date }) => {
                        const selected = id === activeDay;
                        return (
                            <button
                                key={id}
                                id={`tab-${id}`}
                                type="button"
                                role="tab"
                                aria-selected={selected}
                                aria-controls={`agenda-${id}`}
                                onClick={() => setActiveDay(id)}
                                className={`min-w-0 cursor-pointer rounded-xl border px-5 py-3.5 text-center min-[621px]:min-w-[118px] ${selected
                                        ? 'border-acento-principal bg-acento-principal/[0.12] shadow-[inset_0_0_0_1px_rgba(26,178,255,0.18)]'
                                        : 'border-gelo/10 bg-white/[0.025]'
                                    }`}
                            >
                                <span
                                    className={`mb-1 block font-montserrat text-[9px] font-bold uppercase leading-none tracking-[0.13em] ${selected ? 'text-acento-forte' : 'text-cinza-subtil'
                                        }`}
                                >
                                    {tab}
                                </span>
                                <strong
                                    className={`block font-poppins text-lg font-bold leading-[1.1] ${selected ? 'text-acento-forte' : 'text-cinza-texto'
                                        }`}
                                >
                                    {date}
                                </strong>
                            </button>
                        );
                    })}
                </div>

                {days.map((day) => (
                    <div
                        key={day.id}
                        id={`agenda-${day.id}`}
                        role="tabpanel"
                        aria-labelledby={`tab-${day.id}`}
                        hidden={day.id !== activeDay}
                        className="mx-auto max-w-[1120px]"
                    >
                        <p className="mb-[18px] w-fit border-b-2 border-acento-principal pb-2.5 font-montserrat text-[11px] font-bold uppercase leading-none tracking-[0.12em] text-acento-forte">
                            {day.label}
                        </p>
                        {day.items.map((item) => (
                            <ScheduleRow key={`${item.time}-${item.title}`} iso={day.iso} item={item} />
                        ))}
                    </div>
                ))}
            </Section>

            {/* ORADORES */}
            <Section id="oradores">
                <SplitHeading
                    eyebrow="ORADORES"
                    title="As pessoas que vão estar no ENEI."
                    lead="Perfis, organizações e sessões serão revelados à medida que as presenças forem confirmadas."
                    className="mb-[42px]"
                />
                <div
                    aria-label="Oradores a anunciar"
                    className="grid grid-cols-1 gap-3 min-[621px]:grid-cols-2 min-[621px]:gap-3.5 min-[701px]:grid-cols-4"
                >
                    {speakers.map((speaker) => (
                        <SpeakerCard key={speaker.title} {...speaker} />
                    ))}
                </div>
            </Section>

            {/* EIXOS */}
            <Section surface>
                <SectionHeading
                    align="center"
                    eyebrow={<Eyebrow text="3 EIXOS + 1 CAMADA DIGITAL" />}
                    title="Mais do que uma sequência de palestras."
                    lead="A experiência combina competição, aprendizagem e convívio, ligados por uma plataforma de gamificação."
                    className="mb-[42px]"
                    classNameTitle={h2Class}
                    classNameLead={leadClass}
                />
                <div className="grid grid-cols-1 border-y border-acento-principal/[0.42] text-left min-[621px]:grid-cols-2 min-[701px]:grid-cols-4">
                    {axes.map((axis, index) => (
                        <AxisCard key={axis.title} {...axis} index={index} />
                    ))}
                </div>
            </Section>

            {/* EXPERIÊNCIAS */}
            <Section>
                <SplitHeading
                    eyebrow="EXPERIÊNCIAS"
                    title="Do código à cultura algarvia."
                    lead="Atividades para desafiar competências, criar ligações e viver a comunidade académica."
                />
                <div className="grid grid-cols-1 gap-3.5 min-[621px]:grid-cols-2 min-[701px]:grid-cols-3">
                    {experiences.map((experience, index) => (
                        <ExperienceCard key={experience.title} {...experience} index={index} />
                    ))}
                </div>
            </Section>

            {/* PLATAFORMA */}
            <Section
                surface
                contentClassName="grid grid-cols-1 items-center gap-[clamp(40px,8vw,100px)] min-[701px]:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]"
            >
                <SectionHeading
                    eyebrow={<Eyebrow text="PLATAFORMA" />}
                    title="O evento continua no teu telemóvel."
                    lead="A experiência digital recompensa a descoberta do recinto, a interação com oradores e a visita às bancas dos parceiros."
                    className="mb-0"
                    classNameTitle={h2Class}
                    classNameLead={leadClass}
                />

                <div className="grid grid-cols-1 gap-3.5 min-[621px]:grid-cols-2">
                    {platformItems.map(({ title, text, tone, icon }) => (
                        <Tile
                            key={title}
                            tone={tone}
                            rounded
                            showInnerBorder
                            className="min-w-0 p-[22px] min-[621px]:p-[26px]"
                        >
                            <div className="grid grid-cols-[auto_1fr] gap-x-[18px]">
                                <div className="row-span-2 [&>div]:mb-0">
                                    <IconBox tone={tone}>{icon}</IconBox>
                                </div>
                                <h3 className={h3Class}>{title}</h3>
                                <p className="mt-[7px] text-sm text-cinza-texto">{text}</p>
                            </div>
                        </Tile>
                    ))}
                </div>
            </Section>
        </main>
    );
}