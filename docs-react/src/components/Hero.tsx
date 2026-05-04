import { hero } from "../content/docsContent";

export function Hero() {
  return (
    <header className="hero surface">
      <img src="/logo-memoryfeed.svg" alt="MemoryFeed logo" className="logo" />
      <div className="hero-copy">
        <h1>{hero.title}</h1>
        <p>{hero.description}</p>
      </div>
      <div className="badge-row">
        {hero.badges.map((badge) => (
          <span className="badge" key={badge}>
            {badge}
          </span>
        ))}
      </div>
    </header>
  );
}
