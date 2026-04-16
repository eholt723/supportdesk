import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { get, submitTicket, wsUrl } from "../api";

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
// Demo tickets
// ---------------------------------------------------------------------------

const DEMO_TICKETS = [
  {
    email: "alice.morgan@example.com",
    subject: "Still being charged after I cancelled",
    body: "I cancelled my subscription three weeks ago through Settings > Billing, but I was charged again this month. Can you please confirm the cancellation went through and process a refund?",
    label: "Charged after cancellation",
    tag: "billing",
  },
  {
    email: "james.t@example.com",
    subject: "CSV export produces an empty file",
    body: "Every time I export a project as CSV the downloaded file is empty. This started after last week's platform update. I've tried hard-refreshing and a different browser with the same result.",
    label: "CSV export is empty",
    tag: "technical",
  },
  {
    email: "dev.team@example.com",
    subject: "Does Pro include REST API access?",
    body: "We're considering upgrading from Starter to Pro. I want to confirm whether the Pro plan includes REST API access, what the monthly request limit is, and whether webhooks are included.",
    label: "API access on Pro plan",
    tag: "feature",
  },
  {
    email: "sarah.k@example.com",
    subject: "Invite button is grayed out for new members",
    body: "I'm trying to add two new employees to our workspace but the Invite button under Settings > Members is grayed out. We're on the Starter plan — is there a seat limit I'm hitting?",
    label: "Can't invite new members",
    tag: "general",
  },
  {
    email: "mark.r@example.com",
    subject: "Accidentally deleted a task — can it be recovered?",
    body: "I accidentally deleted a task that had several weeks of comments and attachments. Is there any way to recover it? It was deleted about an hour ago and I never meant to remove it permanently.",
    label: "Recover deleted task",
    tag: "technical",
  },
];

const TAG_STYLES = {
  billing: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400",
  technical: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400",
  feature: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-400",
  general: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
};

function DemoTicketPanel({ onSubmitted }) {
  const [states, setStates] = useState(() => Object.fromEntries(DEMO_TICKETS.map((_, i) => [i, "idle"])));

  function setState(i, s) {
    setStates((prev) => ({ ...prev, [i]: s }));
  }

  async function handleSend(i) {
    if (states[i] !== "idle") return;
    setState(i, "sending");
    const { email, subject, body } = DEMO_TICKETS[i];
    try {
      await submitTicket(email, subject, body);
      setState(i, "done");
      onSubmitted();
    } catch {
      setState(i, "error");
      setTimeout(() => setState(i, "idle"), 3000);
    }
  }

  return (
    <div className="space-y-2">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Demo Tickets</h2>
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
        {DEMO_TICKETS.map((t, i) => {
          const s = states[i];
          return (
            <button
              key={i}
              onClick={() => handleSend(i)}
              disabled={s !== "idle"}
              className={`
                text-left rounded-xl border px-3 py-3 transition-colors space-y-2
                ${s === "done"
                  ? "border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 cursor-default"
                  : s === "error"
                  ? "border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 cursor-default"
                  : s === "sending"
                  ? "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 opacity-60 cursor-default"
                  : "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-cyan-300 dark:hover:border-cyan-700 hover:bg-cyan-50/30 dark:hover:bg-cyan-900/10 cursor-pointer"
                }
              `}
            >
              <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${TAG_STYLES[t.tag]}`}>
                {t.tag}
              </span>
              <p className="text-xs font-medium text-gray-800 dark:text-gray-200 leading-snug">{t.label}</p>
              <p className={`text-xs font-medium ${
                s === "done" ? "text-emerald-600 dark:text-emerald-400"
                : s === "error" ? "text-red-500"
                : s === "sending" ? "text-gray-400"
                : "text-cyan-600 dark:text-cyan-400"
              }`}>
                {s === "done" ? "Submitted" : s === "error" ? "Failed — retry" : s === "sending" ? "Sending..." : "Send ticket"}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

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
  const [sortBy, setSortBy] = useState("urgency");
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

  const URGENCY_ORDER = { high: 0, medium: 1, low: 2 };
  const STATUS_ORDER = { pending: 0, sent: 1, approved: 2, discarded: 3 };

  const sortedTickets = [...tickets].sort((a, b) => {
    if (sortBy === "urgency") {
      const u = (URGENCY_ORDER[a.urgency] ?? 3) - (URGENCY_ORDER[b.urgency] ?? 3);
      return u !== 0 ? u : new Date(b.created_at) - new Date(a.created_at);
    }
    if (sortBy === "status") {
      const s = (STATUS_ORDER[a.status] ?? 4) - (STATUS_ORDER[b.status] ?? 4);
      return s !== 0 ? s : new Date(b.created_at) - new Date(a.created_at);
    }
    if (sortBy === "time") {
      return new Date(a.created_at) - new Date(b.created_at);
    }
    return 0;
  });

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

      {/* Demo tickets */}
      <DemoTicketPanel onSubmitted={refreshTickets} />

      {/* Two-column layout: ticket queue + event log */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Ticket queue */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Ticket Queue</h2>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-xs bg-transparent border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 rounded-lg px-2 py-1 focus:outline-none"
            >
              <option value="urgency">Urgency</option>
              <option value="status">Status</option>
              <option value="time">Time in queue</option>
            </select>
          </div>
          <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
            {tickets.length === 0 ? (
              <p className="text-gray-500 text-sm p-6">No tickets yet.</p>
            ) : (
              sortedTickets.map((t) => (
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
