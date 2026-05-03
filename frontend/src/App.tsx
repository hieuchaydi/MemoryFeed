import type { ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";

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
  return (
    <div className="app-shell">
      <aside className="left-rail">
        <div className="brand">
          <img src="/logo-memoryfeed.svg" alt="MemoryFeed logo" className="logo-wordmark" />
        </div>
        <nav className="tabs">
          <Tab to="/">Search</Tab>
          <Tab to="/timeline">Timeline</Tab>
          <Tab to="/stats">Stats</Tab>
        </nav>
        <div className="rail-note">
          <p>AI-powered local archive for social content.</p>
          <small>React + Vite + FastAPI + LanceDB + Native C++</small>
        </div>
      </aside>
      <main className="main-pane">
        <Outlet />
      </main>
    </div>
  );
}
