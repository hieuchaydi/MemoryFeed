import { demoIntro, demoOutcome, demoSteps } from "../content/docsContent";
import { Section } from "./Section";

export function DemoSection() {
  return (
    <>
      <Section title="Demo GIF">
        <img src="/assets/quickstart-demo.gif" alt="Quickstart demo" className="demo" />
        <p className="note">Asset: /public/assets/quickstart-demo.gif</p>
      </Section>

      <Section title="Demo Walkthrough">
        <div className="prose">
          <p>{demoIntro}</p>
        </div>
        <ol className="check-list">
          {demoSteps.map((step, index) => (
            <li key={step}>
              {index === 3 ? (
                <>
                  {step} Example:{" "}
                  <code>angry cat meme from this week</code>.
                </>
              ) : (
                step
              )}
            </li>
          ))}
        </ol>
        <div className="prose">
          <p>{demoOutcome}</p>
        </div>
      </Section>
    </>
  );
}
