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
  const caption = department === 'Direção' ? role
    : role === 'Chefe do Departamento' ? `${role} de ${department}`
    : role ? `${role} · ${department}` : department;
  return (
    <li className={`team-member${hasPhoto ? '' : ' team-member--placeholder'}`}>
      <div className="team-member__portrait">
      <img
        src={photoUrl(photo)}
        alt={hasPhoto ? name : `Mascote do NEEI como fotografia temporária de ${name}`}
        loading="lazy"
        width={480}
        height={480}
      />
      </div>
      <div className="team-member__caption">
        <h3>{name}</h3>
        {caption && <p>{caption}</p>}
      </div>
    </li>
  );
}
