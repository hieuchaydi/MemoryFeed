import { quickstartCards } from "../content/docsContent";
import { InfoGrid } from "./InfoGrid";
import { Section } from "./Section";

export function QuickstartSection() {
  return (
    <Section title="Quickstart">
      <InfoGrid cards={quickstartCards} codeStyle />
    </Section>
  );
}
