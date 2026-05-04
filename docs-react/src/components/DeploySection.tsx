import { deploySteps } from "../content/docsContent";
import { Section } from "./Section";

export function DeploySection() {
  return (
    <Section title="Deploy Docs (Vercel)">
      <ol className="check-list">
        {deploySteps.map((step) => (
          <li key={step}>
            {step.includes("npm ") ? <code>{step}</code> : step}
          </li>
        ))}
      </ol>
    </Section>
  );
}
