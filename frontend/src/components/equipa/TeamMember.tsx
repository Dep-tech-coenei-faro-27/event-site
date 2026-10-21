import type { Member } from "../../data/Team";
import mascot from "../../assets/mascot.webp";

// Fotos da equipa: `src/assets/team/<ficheiro>.webp`. Sem foto (ou ficheiro em falta) mostra a mascote.
const photos = import.meta.glob("../../assets/team/*.webp", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

const photoUrl = (file?: string) => (file && photos[`../../assets/team/${file}.webp`]) || mascot;

type Props = Member & { department: string };

export default function TeamMember({ name, role, photo, department }: Props) {
  const hasPhoto = Boolean(photo && photos[`../../assets/team/${photo}.webp`]);
  return (
    <article className="team-member">
      <img
        src={photoUrl(photo)}
        alt={hasPhoto ? name : `Mascote do NEEI como fotografia temporária de ${name}`}
        loading="lazy"
      />
      <div>
        <h3>{name}</h3>
        <p>{role ? `${role} · ${department}` : department}</p>
      </div>
    </article>
  );
}
