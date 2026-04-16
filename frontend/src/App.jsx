import { useState, useEffect } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import TicketDetail from "./pages/TicketDetail";
import KB from "./pages/KB";
import Submit from "./pages/Submit";
import About from "./pages/About";

const navLinks = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/kb", label: "Knowledge Base" },
  { to: "/about", label: "About" },
];

export default function App() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("dark");
    return stored === null ? true : stored === "true";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("dark", String(dark));
  }, [dark]);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <header className="border-b border-gray-200 dark:border-gray-800 px-4 py-3">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <span className="text-cyan-600 dark:text-cyan-400 font-semibold tracking-tight text-lg">
            SupportDesk
          </span>
          <nav className="flex items-center gap-6 text-sm">
            {navLinks.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  isActive
                    ? "text-cyan-600 dark:text-cyan-400 font-medium"
                    : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                }
              >
                {label}
              </NavLink>
            ))}
            <button
              onClick={() => setDark((d) => !d)}
              aria-label="Toggle dark mode"
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800 transition-colors"
            >
              {dark ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 3v1m0 16v1m8.66-9h-1M4.34 12h-1m15.07-6.07-.71.71M6.34 17.66l-.71.71m12.73 0-.71-.71M6.34 6.34l-.71-.71M12 7a5 5 0 1 0 0 10A5 5 0 0 0 12 7z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/ticket/:id" element={<TicketDetail />} />
          <Route path="/kb" element={<KB />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>

      <footer className="border-t border-gray-200 dark:border-gray-800 text-center text-xs text-gray-400 dark:text-gray-600 py-4 mt-12">
        SupportDesk — AI-powered customer support automation
      </footer>

      <div className="fixed bottom-3 right-4 text-right text-xs pointer-events-none select-none">
        <p className="text-gray-400 dark:text-gray-600">Created by</p>
        <p className="font-medium text-gray-500">Eric Holt</p>
      </div>
    </div>
  );
}
