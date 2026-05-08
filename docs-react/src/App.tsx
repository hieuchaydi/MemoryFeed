import { useEffect, useMemo, useState } from "react";
import { getDocsContent, type CommandBlock, type InfoCard, type Locale } from "./content/localizedContent";
import "./styles.css";

type Theme = "light" | "dark";

type UiCopy = {
  navAria: string;
  standalone: string;
  languageLabel: string;
  themeLabel: string;
  switchToDark: string;
  switchToLight: string;
};

const localeLabels: Record<Locale, string> = {
  vi: "VI",
  en: "EN",
  zh: "\u4e2d\u6587",
};

const uiCopy: Record<Locale, UiCopy> = {
  vi: {
    navAria: "\u0110i\u1ec1u h\u01b0\u1edbng t\u00e0i li\u1ec7u",
    standalone: "Standalone documentation",
    languageLabel: "Ng\u00f4n ng\u1eef",
    themeLabel: "Giao di\u1ec7n",
    switchToDark: "B\u1eadt n\u1ec1n t\u1ed1i",
    switchToLight: "B\u1eadt n\u1ec1n s\u00e1ng",
  },
  en: {
    navAria: "Documentation navigation",
    standalone: "Standalone documentation",
    languageLabel: "Language",
    themeLabel: "Theme",
    switchToDark: "Use dark mode",
    switchToLight: "Use light mode",
  },
  zh: {
    navAria: "\u6587\u6863\u5bfc\u822a",
    standalone: "\u72ec\u7acb\u6587\u6863\u7ad9\u70b9",
    languageLabel: "\u8bed\u8a00",
    themeLabel: "\u4e3b\u9898",
    switchToDark: "\u5207\u6362\u5230\u6df1\u8272",
    switchToLight: "\u5207\u6362\u5230\u6d45\u8272",
  },
};

const THEME_KEY = "memoryfeed-docs-theme";
const LOCALE_KEY = "memoryfeed-docs-locale";

export default function App() {
  const [locale, setLocale] = useState<Locale>(() => getInitialLocale());
  const [theme, setTheme] = useState<Theme>(() => getInitialTheme());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(LOCALE_KEY, locale);
  }, [locale]);

  const content = useMemo(() => getDocsContent(locale), [locale]);
  const copy = uiCopy[locale];

  return (
    <div className="docs-shell">
      <aside className="docs-nav" aria-label={copy.navAria}>
        <img src="/logo-memoryfeed.svg" alt="MemoryFeed logo" className="docs-logo" />

        <div className="control-panel">
          <p>{copy.languageLabel}</p>
          <div className="segmented" role="tablist" aria-label={copy.languageLabel}>
            {Object.keys(localeLabels).map((key) => {
              const next = key as Locale;
              return (
                <button
                  key={next}
                  type="button"
                  className={next === locale ? "is-active" : ""}
                  onClick={() => setLocale(next)}
                  aria-pressed={next === locale}
                >
                  {localeLabels[next]}
                </button>
              );
            })}
          </div>

          <p>{copy.themeLabel}</p>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((prev) => (prev === "light" ? "dark" : "light"))}
            aria-label={theme === "light" ? copy.switchToDark : copy.switchToLight}
            title={theme === "light" ? copy.switchToDark : copy.switchToLight}
          >
            {theme === "light" ? <MoonIcon /> : <SunIcon />}
          </button>
        </div>

        <nav>
          {content.navItems.map((item) => (
            <a key={item.id} href={`#${item.id}`}>
              {item.label}
            </a>
          ))}
        </nav>
      </aside>

      <main className="docs-main">
        <header className="docs-hero">
          <div>
            <p className="eyebrow">{copy.standalone}</p>
            <h1>{content.hero.title}</h1>
            <p>{content.hero.description}</p>
          </div>
          <div className="badge-row">
            {content.hero.badges.map((badge) => (
              <span className="badge" key={badge}>
                {badge}
              </span>
            ))}
          </div>
        </header>

        {content.sections.map((section) => (
          <section className="docs-section" id={section.id} key={section.id}>
            <p className="eyebrow">{section.kicker}</p>
            <h2>{section.title}</h2>

            {section.body?.length ? (
              <div className="prose">
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
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
          {card.lines.map((line) => (
            <p key={`${card.title}-${line}`}>{line}</p>
          ))}
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
          <div className="code-head">
            <h3>{command.title}</h3>
            <CopyButton text={command.code} />
          </div>
          <AnimatedCode code={command.code} />
        </article>
      ))}
    </div>
  );
}

type AnimatedState = {
  lineIndex: number;
  cursor: number;
  mode: "typing" | "hold-line" | "hold-all";
  holdTicks: number;
};

function AnimatedCode({ code }: { code: string }) {
  const lines = useMemo(() => code.split("\n"), [code]);
  const state = useAnimatedLines(lines);

  return (
    <pre>
      <code>
        {lines.map((line, index) => {
          const finished = index < state.lineIndex || (index === state.lineIndex && state.mode === "hold-all");
          const isCurrent = index === state.lineIndex && state.mode !== "hold-all";
          const text = finished ? line : isCurrent ? line.slice(0, state.cursor) : "";

          return (
            <span className={`command-line${isCurrent ? " is-active" : ""}`} key={`${line}-${index}`}>
              {text || " "}
            </span>
          );
        })}
      </code>
    </pre>
  );
}

function useAnimatedLines(lines: string[]) {
  const [state, setState] = useState<AnimatedState>({
    lineIndex: 0,
    cursor: 0,
    mode: "typing",
    holdTicks: 0,
  });

  useEffect(() => {
    setState({
      lineIndex: 0,
      cursor: 0,
      mode: "typing",
      holdTicks: 0,
    });

    const timer = window.setInterval(() => {
      setState((previous) => {
        const total = lines.length;
        if (!total) {
          return previous;
        }

        const target = lines[previous.lineIndex] ?? "";

        if (previous.mode === "typing") {
          if (previous.cursor < target.length) {
            return { ...previous, cursor: previous.cursor + 1 };
          }
          return { ...previous, mode: "hold-line", holdTicks: 10 };
        }

        if (previous.mode === "hold-line") {
          if (previous.holdTicks > 0) {
            return { ...previous, holdTicks: previous.holdTicks - 1 };
          }
          if (previous.lineIndex < total - 1) {
            return { lineIndex: previous.lineIndex + 1, cursor: 0, mode: "typing", holdTicks: 0 };
          }
          return { ...previous, mode: "hold-all", holdTicks: 22 };
        }

        if (previous.holdTicks > 0) {
          return { ...previous, holdTicks: previous.holdTicks - 1 };
        }

        return {
          lineIndex: 0,
          cursor: 0,
          mode: "typing",
          holdTicks: 0,
        };
      });
    }, 56);

    return () => window.clearInterval(timer);
  }, [lines]);

  return state;
}

function Checklist({ items }: { items: string[] }) {
  return (
    <ul className="check-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 5a1 1 0 0 1 1 1v1.1a1 1 0 1 1-2 0V6a1 1 0 0 1 1-1Zm0 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 4a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1Zm7-8a1 1 0 1 1 0 2h-1.1a1 1 0 1 1 0-2H19Zm-12.9 0a1 1 0 1 1 0 2H5a1 1 0 1 1 0-2h1.1Zm9.06-4.06a1 1 0 0 1 1.42 0l.77.78a1 1 0 0 1-1.42 1.41l-.77-.77a1 1 0 0 1 0-1.42Zm-7.32 7.32a1 1 0 0 1 1.42 0l.77.77a1 1 0 1 1-1.42 1.42l-.77-.78a1 1 0 0 1 0-1.41Zm9.74 2.19a1 1 0 0 1 0 1.42l-.77.78a1 1 0 1 1-1.42-1.42l.77-.78a1 1 0 0 1 1.42 0Zm-9.74-9.74a1 1 0 0 1 0 1.42l-.77.77a1 1 0 1 1-1.42-1.41l.77-.78a1 1 0 0 1 1.42 0Z"
        fill="currentColor"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M14.5 2.8a1 1 0 0 1 .7 1.6A7.5 7.5 0 1 0 19.6 15a1 1 0 0 1 1.6.9A9.5 9.5 0 1 1 13.6 2a1 1 0 0 1 .9.8Z"
        fill="currentColor"
      />
    </svg>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      type="button"
      className="copy-btn"
      onClick={onCopy}
      aria-label={copied ? "\u0110\u00e3 sao ch\u00e9p" : "Sao ch\u00e9p l\u1ec7nh"}
      title={copied ? "\u0110\u00e3 sao ch\u00e9p" : "Sao ch\u00e9p l\u1ec7nh"}
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </button>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M9 3a2 2 0 0 0-2 2v2H6a2 2 0 0 0-2 2v9a3 3 0 0 0 3 3h8a2 2 0 0 0 2-2v-1h1a2 2 0 0 0 2-2V8l-5-5H9Zm8 4.4V4.5L19.5 7H17ZM9 5h6v3a1 1 0 0 0 1 1h2v7H9V5Zm-3 4h1v7a2 2 0 0 0 2 2h6v1H7a1 1 0 0 1-1-1V9Z"
        fill="currentColor"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9.2 16.2 5.7 12.7l-1.4 1.4 4.9 4.9L20 8.2l-1.4-1.4-9.4 9.4Z" fill="currentColor" />
    </svg>
  );
}

function getInitialTheme(): Theme {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") {
    return saved;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getInitialLocale(): Locale {
  const saved = localStorage.getItem(LOCALE_KEY);
  if (saved === "vi" || saved === "en" || saved === "zh") {
    return saved;
  }

  return "vi";
}
