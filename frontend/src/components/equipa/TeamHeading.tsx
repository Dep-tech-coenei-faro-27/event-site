import Eyebrow from "../EyeBrow";

type Props = {
  eyebrow: string;
  title: string;
  description: string;
  titleId?: string;
};

/** Eyebrow + título + descrição, com linha por baixo. */
export default function TeamHeading({ eyebrow, title, description, titleId }: Props) {
  return (
    <header className="flex flex-col gap-4 border-b border-ciano-digital/30 pb-6 md:flex-row md:items-end md:justify-between">
      <div>
        <Eyebrow text={eyebrow} />
        <h2 id={titleId} className="mt-2 text-3xl font-bold text-branco">
          {title}
        </h2>
      </div>
      <p className="max-w-md text-cinza-texto md:text-right">{description}</p>
    </header>
  );
}