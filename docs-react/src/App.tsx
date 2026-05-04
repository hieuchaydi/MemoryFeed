import { Hero } from "./components/Hero";
import { IntroSection } from "./components/IntroSection";
import { QuickstartSection } from "./components/QuickstartSection";
import { DemoSection } from "./components/DemoSection";
import { DeploySection } from "./components/DeploySection";
import { ReliabilitySection } from "./components/ReliabilitySection";

export default function App() {
  return (
    <div className="page">
      <Hero />
      <IntroSection />
      <QuickstartSection />
      <DemoSection />
      <DeploySection />
      <ReliabilitySection />
    </div>
  );
}
