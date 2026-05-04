import { InfoGrid } from "./InfoGrid";
import { Section } from "./Section";
import { introCards, introParagraphs } from "../content/docsContent";

export function IntroSection() {
  return (
    <Section title="Introduction">
      <div className="prose">
        {introParagraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
      <InfoGrid cards={introCards} />
    </Section>
  );
}
