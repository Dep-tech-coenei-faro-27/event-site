export type Tone = 'cyan' | 'teal' | 'sand' | 'coral' | 'periwinkle';

export interface ToneConfig {
    color: string;
    icon: string;
}

export const tones: Record<Tone, ToneConfig> = {
    cyan: { color: '#28C2FF', icon: 'border-ciano-icone/50 bg-ciano-icone/10 text-ciano-icone' },
    teal: { color: '#5BD6C4', icon: 'border-verde-agua/45 bg-verde-agua/10 text-verde-agua' },
    sand: { color: '#E5BF78', icon: 'border-areia/45 bg-areia/10 text-areia' },
    coral: { color: '#EE9185', icon: 'border-coral-suave/45 bg-coral-suave/10 text-coral-suave' },
    periwinkle: { color: '#AAB4FF', icon: 'border-pervinca/45 bg-pervinca/10 text-pervinca' },
};