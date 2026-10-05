import type { CSSProperties, ReactNode } from 'react';
import azulejoPattern from '../assets/azulejo-pattern-transparent.webp';

type Tone = 'cyan' | 'teal' | 'sand' | 'coral' | 'periwinkle';

interface TileProps {
    tone: Tone;
    pattern?: boolean;
    className?: string;
    children: ReactNode;
}

interface ToneConfig {
    color: string;
}

const tones: Record<Tone, ToneConfig> = {
    cyan: {
        color: '#28C2FF',
    },
    teal: {
        color: '#5BD6C4',
    },
    sand: {
        color: '#E5BF78',
    },
    coral: {
        color: '#EE9185',
    },
    periwinkle: {
        color: '#AAB4FF',
    },
};

export default function Tile({
    tone,
    pattern = false,
    className = '',
    children,
}: TileProps) {
    return (
        <article
            style={
                {
                    '--tile-color': tones[tone].color,
                } as CSSProperties
            }
            className={`
                relative overflow-hidden rounded-lg border border-t-[3px]
                border-[color:color-mix(in_srgb,var(--tile-color)_34%,rgba(215,227,244,0.1))]
                border-t-[color:var(--tile-color)]
                bg-azul-painel
                bg-[linear-gradient(145deg,color-mix(in_srgb,var(--tile-color)_10%,transparent),transparent_60%)]
                shadow-[0_16px_34px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.025)]
                ${className}
            `}
        >
            {pattern && (
                <span
                    aria-hidden="true"
                    className="pointer-events-none absolute inset-0 bg-[color:var(--tile-color)] opacity-[0.055]"
                    style={{
                        WebkitMaskImage: `url(${azulejoPattern})`,
                        maskImage: `url(${azulejoPattern})`,
                        WebkitMaskSize: '88px 88px',
                        maskSize: '88px 88px',
                        WebkitMaskPosition: 'center',
                        maskPosition: 'center',
                        WebkitMaskRepeat: 'repeat',
                        maskRepeat: 'repeat',
                    }}
                />
            )}

            <span
                aria-hidden="true"
                className="
                    pointer-events-none absolute inset-[10px]
                    rounded-[3px]
                    border
                    border-[color:color-mix(in_srgb,var(--tile-color)_14%,transparent)]
                "
            />

            <div className="relative z-10">
                {children}
            </div>
        </article>
    );
}