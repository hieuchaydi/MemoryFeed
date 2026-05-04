import type { ReactNode } from "react";

type SectionProps = {
  title: string;
  children: ReactNode;
};

export function Section({ title, children }: SectionProps) {
  return (
    <section className="surface">
      <h2 className="section-title">{title}</h2>
      {children}
    </section>
  );
}
