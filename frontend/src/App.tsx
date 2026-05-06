import { Link, NavLink, Route, Routes } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Strategies from "./pages/Strategies";
import Backtests from "./pages/Backtests";
import Pools from "./pages/Pools";

function NavTab({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive
            ? "bg-slate-800 text-cyan-300"
            : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <span className="text-2xl font-mono text-cyan-300">⟁</span>
            <span className="font-semibold text-lg">MEV Strategy Lab</span>
          </Link>
          <nav className="flex items-center gap-2">
            <NavTab to="/">Dashboard</NavTab>
            <NavTab to="/strategies">Strategies</NavTab>
            <NavTab to="/backtests">Backtests</NavTab>
            <NavTab to="/pools">Pools</NavTab>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-6xl mx-auto px-6 py-8 w-full">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/backtests" element={<Backtests />} />
          <Route path="/pools" element={<Pools />} />
        </Routes>
      </main>
      <footer className="border-t border-slate-800 py-3 text-center text-xs text-slate-500">
        MEV Strategy Lab · simulator only · not for production trading
      </footer>
    </div>
  );
}
