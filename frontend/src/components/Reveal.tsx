import type { ElementType, ReactNode } from 'react';
import { useInView } from './UseInView';

type Direction = 'up' | 'left' | 'right' | 'none' | 'clip';

interface RevealProps {
    /** Elemento HTML a desenhar. Por omissão, um div. */
    as?: ElementType;
    direction?: Direction;
    delay?: number;
    duration?: number;
    className?: string;
    children: ReactNode;
}

const hidden: Record<Direction, string> = {
    up: 'translate-y-6 opacity-0',
    left: '-translate-x-8 opacity-0',
    right: 'translate-x-8 opacity-0',
    none: 'opacity-0',
    clip: '[clip-path:inset(0_100%_0_0)]',
};

const shown: Record<Direction, string> = {
    up: 'translate-y-0 opacity-100',
    left: 'translate-x-0 opacity-100',
    right: 'translate-x-0 opacity-100',
    none: 'opacity-100',
    clip: '[clip-path:inset(0_0_0_0)]',
};

export default function Reveal({
    as: Tag = 'div',
    direction = 'up',
    delay = 0,
    duration = 700,
    className = '',
    children,
}: RevealProps) {
    const { ref, inView } = useInView<HTMLElement>();

    return (
        <Tag
            ref={ref}
            style={{ transitionDelay: `${delay}ms`, transitionDuration: `${duration}ms` }}
            className={`transition-[opacity,transform,clip-path] ease-out motion-reduce:!translate-x-0 motion-reduce:!translate-y-0 motion-reduce:!opacity-100 motion-reduce:![clip-path:none] motion-reduce:transition-none ${
                inView ? shown[direction] : hidden[direction]
            } ${className}`}
        >
            {children}
        </Tag>
    );
}