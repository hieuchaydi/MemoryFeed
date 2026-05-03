import { NavLink, Outlet } from "react-router-dom";

function Tab({ to, children }) {
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
          <div className="sig">MF</div>
          <div>
            <h3>MemoryFeed</h3>
            <p>Local Memory Graph</p>
          </div>
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
