import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useSettings } from "./settings";

interface TabProps {
  to: string;
  children: ReactNode;
}

function Tab({ to, children }: TabProps) {
  return (
    <NavLink to={to} className={({ isActive }) => `tab ${isActive ? "active" : ""}`}>
      {children}
    </NavLink>
  );
}

export default function App() {
  const { language, setLanguage, setTheme, t, theme } = useSettings();

  return (
    <div className="app-shell">
      <aside className="left-rail">
        <div className="brand">
          <img src="/logo-memoryfeed.svg" alt="MemoryFeed logo" className="logo-wordmark" />
          <p>{t.app.tagline}</p>
        </div>
        <div className="rail-controls" aria-label="Display settings">
          <div className="segmented" aria-label={t.app.theme.label}>
            <button type="button" className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")}>
              {t.app.theme.light}
            </button>
            <button type="button" className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")}>
              {t.app.theme.dark}
            </button>
          </div>
          <div className="segmented" aria-label={t.app.language.label}>
            <button type="button" className={language === "vi" ? "active" : ""} onClick={() => setLanguage("vi")}>
              {t.app.language.vi}
            </button>
            <button type="button" className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>
              {t.app.language.en}
            </button>
          </div>
        </div>
        <nav className="tabs">
          <Tab to="/">{t.app.nav.search}</Tab>
          <Tab to="/feed">{t.app.nav.feed}</Tab>
          <Tab to="/timeline">{t.app.nav.timeline}</Tab>
          <Tab to="/stats">{t.app.nav.stats}</Tab>
        </nav>
        <div className="rail-note">
          <p>{t.app.stack}</p>
          <small>{t.app.local}</small>
        </div>
      </aside>
      <main className="main-pane">
        <Outlet />
      </main>
    </div>
  );
}
