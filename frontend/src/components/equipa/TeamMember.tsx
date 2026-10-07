import type { Member } from "../../data/Team";

// Carrega todas as fotos de src/assets/team/ (Vite 5+).
// Se a foto não existir, usa a mascote.
const photos = import.meta.glob("../../assets/*.webp", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

const photoUrl = (file: string) =>
  photos[`../../assets/team/${file}.webp`] ?? photos["../../assets/mascot.webp"];

type Props = Member & { department: string };

export default function TeamMember({ name, role, photo, department }: Props) {
  return (
    <article className="flex h-full flex-col border border-ciano-digital/20 bg-azul-superficie">
      <img
        src={photoUrl(photo ?? "mascot")}
        alt={photo ? name : `Mascote do NEEI como fotografia temporária de ${name}`}
        loading="lazy"
        className="aspect-square w-full bg-azul-elevado object-cover"
      />
      <div className="flex-1 p-5">
        <h3 className="text-lg font-bold leading-snug text-branco">{name}</h3>
        <p className="mt-2 flex items-center gap-2 text-xs text-cinza-texto">
          <span aria-hidden="true" className="h-0.5 w-2.5 bg-acento-principal" />
          {role ? `${role} · ${department}` : department}
        </p>
      </div>
    </article>
  );
}