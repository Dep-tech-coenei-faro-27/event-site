type Props = { src: string; alt: string; subject: string; priority?: boolean };

/** Imagens de referência locais, a substituir pelas fotografias finais. */
export default function PreviewPhoto({ src, alt, subject, priority = false }: Props) {
  return (
    <figure className="preview-photo">
      <img src={src} alt={alt} loading={priority ? 'eager' : 'lazy'} />
      <figcaption><span>{subject}</span></figcaption>
    </figure>
  );
}
