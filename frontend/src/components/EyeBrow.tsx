interface EyebrowProps {
    text: string;
}

export default function Eyebrow({ text }: EyebrowProps) {
    return (
        <p className="text-acento-forte font-montserrat font-bold text-[11px] leading-[1.4] trackin-[0.16em] uppercase mb-3.5 m-0">
            &lt;{text} /&gt;
        </p>
    );
}