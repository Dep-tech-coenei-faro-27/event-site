import type { CSSProperties, ReactNode } from 'react';
import azulejoPattern from '../assets/azulejo-pattern-transparent.webp';
import { tones, type Tone } from './Tones.ts';

export interface IconBoxProps {
    tone: Tone;
    children: ReactNode;
}

export interface TileProps {
    tone: Tone;
    pattern?: boolean;
    rounded?: boolean;
    showInnerBorder?: boolean;
    className?: string;
    children: ReactNode;
}

/* ---------- Componente IconBox (Exportado) ---------- */

export const IconBox = ({ tone, children }: IconBoxProps) => (
    <div
        aria-hidden="true"
        className={`mb-5 grid h-[52px] w-[52px] place-items-center rounded-[11px] border ${tones[tone].icon}`}
    >
        <svg
            viewBox="0 0 24 24"
            focusable="false"
            className="h-6 w-6 overflow-visible fill-none stroke-current stroke-[1.75] [stroke-linecap:round] [stroke-linejoin:round]"
        >
            {children}
        </svg>
    </div>
);

/* ---------- Componente Principal Tile (Exportado por Defeito) ---------- */

export default function Tile({
    tone,
    pattern = false,
    rounded = false,
    showInnerBorder = false,
    className = '',
    children,
}: TileProps) {
    return (
        <article
            style={{ '--tile-color': tones[tone].color } as CSSProperties}
            className={`
                relative overflow-hidden border border-t-[3px]
                border-[color:color-mix(in_srgb,var(--tile-color)_34%,rgba(215,227,244,0.1))]
                border-t-[color:var(--tile-color)]
                bg-azul-painel
                bg-[linear-gradient(145deg,color-mix(in_srgb,var(--tile-color)_10%,transparent),transparent_60%)]
                shadow-[0_16px_34px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.025)]
                ${rounded ? 'rounded-lg' : ''} 
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

            {showInnerBorder && (
                <span
                    aria-hidden="true"
                    className={`
                        pointer-events-none absolute inset-[10px] border
                        border-[color:color-mix(in_srgb,var(--tile-color)_14%,transparent)]
                        ${rounded ? 'rounded-[3px]' : ''} 
                    `}
                />
            )}

            <div className="relative z-10">
                {children}
            </div>
        </article>
    );
}