import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { get } from "../api";
import { wsUrl } from "../api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });
}

function fmtAge(iso) {
  if (!iso) return "";
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

// ---------------------------------------------------------------------------
// Badges
// ---------------------------------------------------------------------------

function UrgencyBadge({ urgency }) {
  const styles = {
    high: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
    medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
    low: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[urgency] ?? styles.low}`}>
      {urgency ?? "—"}
    </span>
  );
}

function TypeBadge({ type }) {
  const styles = {
    billing: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400",
    technical: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400",
    feature_request: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-400",
    escalation: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-400",
    general: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[type] ?? styles.general}`}>
      {type?.replace("_", " ") ?? "—"}
    </span>
  );
}

function StatusBadge({ status }) {
  const styles = {
    pending: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
    approved: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400",
    sent: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400",
    discarded: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] ?? ""}`}>
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Event type colors for the live log
// ---------------------------------------------------------------------------

const EVENT_COLORS = {
  WEBHOOK:  "text-cyan-500",
  CLASSIFY: "text-violet-400",
  SEARCH:   "text-blue-400",
  DRAFT:    "text-emerald-400",
  PENDING:  "text-amber-400",
  APPROVED: "text-green-400",
  SENT:     "text-emerald-400",
  ERROR:    "text-red-400",
  ping:     "text-gray-600",
};

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 text-center">
      <div className="text-2xl font-semibold text-cyan-600 dark:text-cyan-400">{value ?? "—"}</div>
      <div className="text-xs text-gray-500 mt-1 leading-tight">{label}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const [tickets, setTickets] = useState([]);
  const [events, setEvents] = useState([]);
  const [wsStatus, setWsStatus] = useState("connecting");
  const logRef = useRef(null);
  const wsRef = useRef(null);

  // Load tickets
  useEffect(() => {
    get("/api/tickets")
      .then(setTickets)
      .catch(() => {});
  }, []);

  // Refresh ticket list when pipeline events arrive
  const refreshTickets = () => {
    get("/api/tickets").then(setTickets).catch(() => {});
  };

  // WebSocket event log
  useEffect(() => {
    function connect() {
      const ws = new WebSocket(wsUrl("/api/events/ws"));
      wsRef.current = ws;

      ws.onopen = () => setWsStatus("live");
      ws.onclose = () => {
        setWsStatus("reconnecting");
        setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "ping") return;
        setEvents((prev) => {
          const next = [data, ...prev].slice(0, 100);
          return next;
        });
        // Refresh ticket list on any pipeline event
        if (["WEBHOOK", "CLASSIFY", "DRAFT", "APPROVED", "SENT"].includes(data.type)) {
          refreshTickets();
        }
      };
    }
    connect();
    return () => wsRef.current?.close();
  }, []);

  // Auto-scroll log to top (newest first)
  useEffect(() => {
    logRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [events]);

  const stats = {
    total: tickets.length,
    pending: tickets.filter((t) => t.status === "pending").length,
    sent: tickets.reduce((sum, t) => sum + (t.sent_count ?? 0), 0),
    high: tickets.filter((t) => t.urgency === "high").length,
  };

  return (
    <div className="space-y-6">

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total Tickets" value={stats.total} />
        <StatCard label="Awaiting Review" value={stats.pending} />
        <StatCard label="Sent" value={stats.sent} />
        <StatCard label="High Urgency" value={stats.high} />
      </div>

      {/* Two-column layout: ticket queue + event log */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Ticket queue */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Ticket Queue</h2>
          <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
            {tickets.length === 0 ? (
              <p className="text-gray-500 text-sm p-6">No tickets yet.</p>
            ) : (
              tickets.map((t) => (
                <Link
                  key={t.id}
                  to={`/ticket/${t.id}`}
                  className="flex items-start justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <UrgencyBadge urgency={t.urgency} />
                      <TypeBadge type={t.type} />
                      <StatusBadge status={t.status} />
                    </div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{t.subject}</p>
                    <p className="text-xs text-gray-500">{t.source_email}</p>
                  </div>
                  <div className="shrink-0 ml-4 text-right space-y-1">
                    <p className="text-xs text-gray-400">{fmtAge(t.created_at)}</p>
                    {t.confidence_score != null && (
                      <p className="text-xs text-gray-500">
                        {Math.round(t.confidence_score * 100)}% conf
                      </p>
                    )}
                    {t.sent_at ? (
                      <p className="text-xs text-emerald-500">
                        Sent {new Date(t.sent_at).toLocaleDateString("en-US", { month: "numeric", day: "numeric", year: "numeric" })}
                      </p>
                    ) : (
                      <p className="text-xs text-gray-400">
                        {t.stage_count === 3 ? "pipeline done" : t.stage_count > 0 ? `stage ${t.stage_count}/3` : "queued"}
                      </p>
                    )}
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Live event log */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Live Events</h2>
            <span className={`text-xs flex items-center gap-1.5 ${wsStatus === "live" ? "text-emerald-500" : "text-amber-500"}`}>
              <span className={`w-1.5 h-1.5 rounded-full inline-block ${wsStatus === "live" ? "bg-emerald-500" : "bg-amber-400"}`} />
              {wsStatus}
            </span>
          </div>
          <div
            ref={logRef}
            className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-950 font-mono text-xs p-3 space-y-1 overflow-y-auto"
            style={{ height: "420px" }}
          >
            {events.length === 0 ? (
              <p className="text-gray-600">Waiting for events...</p>
            ) : (
              events.map((ev, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-gray-600 shrink-0">{ev.time}</span>
                  <span className={`shrink-0 w-20 ${EVENT_COLORS[ev.type] ?? "text-gray-400"}`}>
                    [{ev.type}]
                  </span>
                  <span className="text-gray-300 break-all">{ev.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
