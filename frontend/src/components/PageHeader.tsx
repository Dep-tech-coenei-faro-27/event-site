import type { CSSProperties, ReactNode } from 'react';

interface PageHeaderProps {
    backgroundImage: string;
    backgroundPosition?: string;
    overlay?: string;
    align?: 'end' | 'center';
    fadeTo?: string;
    className?: string;
    children: ReactNode;
    minHeight?: string;
}

const DEFAULT_OVERLAY =
    'linear-gradient(90deg, rgba(5,13,33,0.94), rgba(5,13,33,0.66) 58%, rgba(5,13,33,0.36))';

const alignClass = {
    end: 'items-end',
    center: 'items-center',
} as const;

export default function PageHeader({
    minHeight = 'min-h-[560px]',
    backgroundImage,
    backgroundPosition = 'center 48%',
    overlay = DEFAULT_OVERLAY,
    align = 'end',
    fadeTo = 'to-azul-superficie',
    className = '',
    children,
}: PageHeaderProps) {
    const style: CSSProperties = {
        backgroundImage: `${overlay}, url(${backgroundImage})`,
        backgroundPosition: `center, ${backgroundPosition}`,
        backgroundSize: 'cover, cover',
        backgroundRepeat: 'no-repeat, no-repeat',
    };

    return (
        <header
            style={style}
            className={`relative grid ${minHeight} ${alignClass[align]} overflow-hidden border-b border-gelo/10 bg-azul-base ${className}`}
        >
            <div className="relative z-10 mx-auto w-[calc(100%-28px)] max-w-[1180px] min-[621px]:w-[calc(100%-40px)]">{children}</div>

            <div
                aria-hidden="true"
                className={`pointer-events-none absolute inset-x-0 -bottom-px z-[5] h-[clamp(120px,18vw,220px)] bg-gradient-to-b from-transparent ${fadeTo}`}
            />
        </header>
    );
}