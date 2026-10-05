import type { CSSProperties, ReactNode } from 'react';

interface PageHeaderProps {
    backgroundImage: string;
    backgroundPosition?: string;
    className?: string;
    children: ReactNode;
}

export default function PageHeader({
    backgroundImage,
    backgroundPosition = 'center 48%',
    className = '',
    children,
}: PageHeaderProps) {
    const style: CSSProperties = {
        backgroundImage: `linear-gradient(90deg, rgba(5,13,33,0.94), rgba(5,13,33,0.66) 58%, rgba(5,13,33,0.36)), url(${backgroundImage})`,
        backgroundPosition: `center, ${backgroundPosition}`,
        backgroundSize: 'cover, cover',
        backgroundRepeat: 'no-repeat, no-repeat',
    };

    return (
        <header
            style={style}
            className={`relative grid min-h-[560px] items-end overflow-hidden border-b border-gelo/10 bg-azul-base ${className}`}
        >
            <div className="mx-auto w-[calc(100%-40px)] max-w-[1180px]">{children}</div>
        </header>
    );
}