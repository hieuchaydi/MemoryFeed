import { hero, navItems, sections, type CommandBlock, type InfoCard } from "./content/docsContent";
import "./styles.css";

export default function App() {
  return (
    <div className="docs-shell">
      <aside className="docs-nav" aria-label="Docs navigation">
        <img src="/logo-memoryfeed.svg" alt="MemoryFeed logo" className="docs-logo" />
        <nav>
          {navItems.map((item) => (
            <a key={item.id} href={`#${item.id}`}>
              {item.label}
            </a>
          ))}
        </nav>
      </aside>

      <main className="docs-main">
        <header className="docs-hero">
          <div>
            <p className="eyebrow">Standalone documentation</p>
            <h1>{hero.title}</h1>
            <p>{hero.description}</p>
          </div>
          <div className="badge-row">
            {hero.badges.map((badge) => (
              <span className="badge" key={badge}>{badge}</span>
            ))}
          </div>
        </header>

        {sections.map((section) => (
          <section className="docs-section" id={section.id} key={section.id}>
            <p className="eyebrow">{section.kicker}</p>
            <h2>{section.title}</h2>

            {section.body?.length ? (
              <div className="prose">
                {section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
              </div>
            ) : null}

            {section.cards?.length ? <CardGrid cards={section.cards} /> : null}
            {section.commands?.length ? <CommandGrid commands={section.commands} /> : null}
            {section.checklist?.length ? <Checklist items={section.checklist} /> : null}
          </section>
        ))}
      </main>
    </div>
  );
}

function CardGrid({ cards }: { cards: InfoCard[] }) {
  return (
    <div className="card-grid">
      {cards.map((card) => (
        <article className="panel" key={card.title}>
          <h3>{card.title}</h3>
          {card.lines.map((line) => <p key={`${card.title}-${line}`}>{line}</p>)}
        </article>
      ))}
    </div>
  );
}

function CommandGrid({ commands }: { commands: CommandBlock[] }) {
  return (
    <div className="command-grid">
      {commands.map((command) => (
        <article className="code-panel" key={command.title}>
          <h3>{command.title}</h3>
          <pre><code>{command.code}</code></pre>
        </article>
      ))}
    </div>
  );
}

function Checklist({ items }: { items: string[] }) {
  return (
    <ul className="check-list">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  );
}

