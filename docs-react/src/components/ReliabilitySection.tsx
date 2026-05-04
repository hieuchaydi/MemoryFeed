import { reliabilityPoints } from "../content/docsContent";
import { Section } from "./Section";

export function ReliabilitySection() {
  return (
    <Section title="Why This Repo Deploys Cleanly">
      <ul className="check-list">
        {reliabilityPoints.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </Section>
  );
}
