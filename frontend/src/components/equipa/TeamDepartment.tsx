import type { Department } from "../../data/Team";
import TeamMember from "./TeamMember";

/** Um departamento (`ui-ux/equipa`): cabeçalho com a descrição e a grelha de pessoas, todas com o mesmo formato. */
export default function TeamDepartment({ id, label, eyebrow, title, description, members }: Department) {
  const titleId = `${id}-title`;
  return (
    <section className="section team-department" aria-labelledby={titleId}>
      <div className="container">
        <header className="team-department__header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2 id={titleId}>{title}</h2>
          </div>
          <p>{description}</p>
        </header>
        <div className="team-members">
          {members.map((member) => (
            <TeamMember key={`${id}-${member.name}`} {...member} department={label} />
          ))}
        </div>
      </div>
    </section>
  );
}
