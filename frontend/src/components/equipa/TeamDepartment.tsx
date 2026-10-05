import type { Department } from "../../data/Team";
import TeamSection from "./TeamSection";
import TeamHeading from "./TeamHeading";
import TeamMember from "./TeamMember";

type Props = Department & { alternate?: boolean };

export default function TeamDepartment({
  id, label, eyebrow, title, description, members, alternate = false,
}: Props) {
  const titleId = `${id}-title`;
  return (
    <TeamSection tone={alternate ? "azulejo" : "light"} labelledBy={titleId}>
      <TeamHeading
        eyebrow={eyebrow}
        title={title}
        description={description}
        titleId={titleId}
      />
      <div className="mt-8 grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4">
        {members.map((m) => (
          <TeamMember key={`${id}-${m.name}`} {...m} department={label} />
        ))}
      </div>
    </TeamSection>
  );
}