import type { InfoCard } from "../content/docsContent";

type InfoGridProps = {
  cards: InfoCard[];
  codeStyle?: boolean;
};

export function InfoGrid({ cards, codeStyle = false }: InfoGridProps) {
  return (
    <div className="card-grid">
      {cards.map((card) => (
        <article className="panel" key={card.title}>
          <h3>{card.title}</h3>
          {card.lines.map((line) =>
            codeStyle ? (
              <pre key={`${card.title}-${line}`}>{line}</pre>
            ) : (
              <p key={`${card.title}-${line}`}>{line}</p>
            )
          )}
        </article>
      ))}
    </div>
  );
}
