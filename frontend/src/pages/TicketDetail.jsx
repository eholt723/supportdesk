import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { get, post, sseUrl } from "../api";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

// ---------------------------------------------------------------------------
// Badges (duplicated from Dashboard to keep pages self-contained)
// ---------------------------------------------------------------------------

function Badge({ label, color }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>{label}</span>
  );
}

function UrgencyBadge({ urgency }) {
  const styles = {
    high: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
    medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
    low: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  };
  return <Badge label={urgency ?? "—"} color={styles[urgency] ?? styles.low} />;
}

function TypeBadge({ type }) {
  const styles = {
    billing: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-400",
    technical: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400",
    feature_request: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-400",
    escalation: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-400",
    general: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  };
  return <Badge label={type?.replace("_", " ") ?? "—"} color={styles[type] ?? styles.general} />;
}

// ---------------------------------------------------------------------------
// Pipeline stage indicator
// ---------------------------------------------------------------------------

function PipelineStages({ stages }) {
  const ORDER = ["classify", "search", "draft"];
  const byStage = Object.fromEntries(stages.map((s) => [s.stage, s]));

  return (
    <div className="flex items-center gap-0">
      {ORDER.map((name, i) => {
        const s = byStage[name];
        const status = s?.status ?? "pending";
        const dot =
          status === "completed" ? "bg-emerald-500" :
          status === "running"   ? "bg-amber-400 animate-pulse" :
          status === "failed"    ? "bg-red-500" :
          "bg-gray-300 dark:bg-gray-700";
        return (
          <div key={name} className="flex items-center">
            <div className="flex flex-col items-center gap-0.5">
              <div className={`w-3 h-3 rounded-full ${dot}`} title={status} />
              <span className="text-xs text-gray-500 capitalize">{name}</span>
              {s?.duration_ms && (
                <span className="text-xs text-gray-400">{s.duration_ms}ms</span>
              )}
            </div>
            {i < ORDER.length - 1 && (
              <div className={`w-8 h-px mx-1 mb-5 ${s?.status === "completed" ? "bg-emerald-500" : "bg-gray-200 dark:bg-gray-700"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// KB source modal
// ---------------------------------------------------------------------------

function SourceModal({ source, onClose }) {
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get(`/api/kb/chunks?document_name=${encodeURIComponent(source.document_name)}&limit=100`)
      .then(setChunks)
      .catch(() => setChunks([]))
      .finally(() => setLoading(false));
  }, [source.document_name]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="relative bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800 shrink-0">
          <div>
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{source.document_name}</p>
            <p className="text-xs text-gray-500 mt-0.5">Knowledge base source</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-lg leading-none"
          >
            &#10005;
          </button>
        </div>
        <div className="overflow-y-auto p-5 space-y-3">
          {loading ? (
            <p className="text-sm text-gray-400">Loading chunks...</p>
          ) : chunks.length === 0 ? (
            <p className="text-sm text-gray-400">No chunks found.</p>
          ) : (
            chunks.map((chunk, i) => (
              <div
                key={chunk.id}
                className={`rounded-lg p-3 space-y-1 border ${chunk.chunk_text === source.chunk_text
                  ? "border-cyan-400 dark:border-cyan-600 bg-cyan-50 dark:bg-cyan-900/20"
                  : "border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-950"
                }`}
              >
                <p className="text-xs text-cyan-600 dark:text-cyan-400 font-mono">chunk {i + 1}</p>
                <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">{chunk.chunk_text}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Source passage card
// ---------------------------------------------------------------------------

function SourceCard({ source, index, onOpen }) {
  const score = source.score ?? 0;
  const pct = Math.round(score * 100);
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 p-4 space-y-2">
      <div className="flex items-center justify-between">
        <button
          onClick={() => onOpen(source)}
          className="text-xs font-medium text-cyan-600 dark:text-cyan-400 hover:underline text-left"
        >
          [{index + 1}] {source.document_name}
        </button>
        <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${
          pct >= 80 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400" :
          pct >= 60 ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400" :
          "bg-gray-100 text-gray-500 dark:bg-gray-800"
        }`}>
          {pct}% match
        </span>
      </div>
      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">{source.chunk_text}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function TicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Draft streaming
  const [streamedText, setStreamedText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [editedText, setEditedText] = useState(null); // null = show draft, string = editing
  const [approving, setApproving] = useState(false);
  const [actionResult, setActionResult] = useState(null); // {ok, message}
  const [modalSource, setModalSource] = useState(null);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    get(`/api/tickets/${id}`)
      .then((t) => {
        setTicket(t);
        // If draft exists already, show it; otherwise start SSE stream
        if (t.draft?.draft_text) {
          setStreamedText(t.draft.draft_text);
        } else {
          startStream();
        }
      })
      .catch(() => setError("Ticket not found"))
      .finally(() => setLoading(false));
  }, [id]);

  function startStream() {
    setStreaming(true);
    setStreamedText("");
    const es = new EventSource(sseUrl(`/api/tickets/${id}/stream`));
    es.onmessage = (e) => {
      if (e.data === "[DONE]" || e.data === "[TIMEOUT]") {
        es.close();
        setStreaming(false);
        // Reload ticket to get persisted draft + sources
        get(`/api/tickets/${id}`).then(setTicket).catch(() => {});
        return;
      }
      setStreamedText((prev) => prev + e.data.replace(/\\n/g, "\n"));
    };
    es.onerror = () => {
      es.close();
      setStreaming(false);
    };
  }

  async function handleApprove() {
    setApproving(true);
    try {
      await post(`/api/tickets/${id}/approve`, { agent_name: "agent" });
      setActionResult({ ok: true, message: "Reply sent to customer." });
      get(`/api/tickets/${id}`).then(setTicket).catch(() => {});
    } catch (e) {
      setActionResult({ ok: false, message: e.message });
    } finally {
      setApproving(false);
    }
  }

  async function handleDiscard() {
    try {
      await post(`/api/tickets/${id}/discard`, {});
      navigate("/");
    } catch (e) {
      setActionResult({ ok: false, message: e.message });
    }
  }

  async function handleReset() {
    setResetting(true);
    try {
      await post(`/api/tickets/${id}/reset`, {});
      setStreamedText("");
      setEditedText(null);
      setActionResult(null);
      const t = await get(`/api/tickets/${id}`);
      setTicket(t);
      startStream();
    } catch (e) {
      setActionResult({ ok: false, message: e.message });
    } finally {
      setResetting(false);
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading...</p>;
  if (error) return <p className="text-red-500 text-sm">{error}</p>;
  if (!ticket) return null;

  const draft = ticket.draft;
  const sources = draft?.sources_used ?? [];
  const displayText = editedText !== null ? editedText : streamedText;
  const isPending = ticket.status === "pending";

  return (
    <div className="space-y-6 max-w-4xl">
      {modalSource && <SourceModal source={modalSource} onClose={() => setModalSource(null)} />}

      {/* Back link */}
      <Link to="/" className="text-sm text-cyan-600 dark:text-cyan-400 hover:underline">
        &larr; Back to dashboard
      </Link>

      {/* Ticket header */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100 leading-snug">
              {ticket.subject}
            </h1>
            <p className="text-sm text-gray-500">{ticket.source_email}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
            <UrgencyBadge urgency={ticket.urgency} />
            <TypeBadge type={ticket.type} />
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              ticket.status === "sent" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400" :
              ticket.status === "pending" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400" :
              "bg-gray-100 text-gray-500 dark:bg-gray-800"
            }`}>
              {ticket.status}
            </span>
          </div>
        </div>
        <div className="rounded-lg bg-gray-50 dark:bg-gray-950 border border-gray-100 dark:border-gray-800 p-4 text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
          {ticket.body}
        </div>
      </div>

      {/* Pipeline stages */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 space-y-2">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Pipeline</h2>
        <PipelineStages stages={ticket.pipeline_stages ?? []} />
      </div>

      {/* RAG sources */}
      {sources.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Sources Used ({sources.length})
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {sources.map((s, i) => <SourceCard key={i} source={s} index={i} onOpen={setModalSource} />)}
          </div>
        </div>
      )}

      {/* Draft response */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Draft Response
            {streaming && (
              <span className="ml-2 text-xs text-amber-400 font-normal animate-pulse">generating...</span>
            )}
            {draft?.confidence_score && (
              <span className="ml-2 text-xs text-gray-500 font-normal">
                {Math.round(draft.confidence_score * 100)}% confidence
              </span>
            )}
          </h2>
          {!streaming && displayText && isPending && editedText === null && (
            <button
              onClick={() => setEditedText(displayText)}
              className="text-xs text-cyan-600 dark:text-cyan-400 hover:underline"
            >
              Edit
            </button>
          )}
          {editedText !== null && (
            <button
              onClick={() => setEditedText(null)}
              className="text-xs text-gray-500 hover:underline"
            >
              Reset
            </button>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          {editedText !== null ? (
            <textarea
              className="w-full p-5 bg-transparent text-sm text-gray-700 dark:text-gray-300 leading-relaxed resize-none outline-none min-h-64"
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              rows={12}
            />
          ) : (
            <div className="p-5 text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap min-h-32">
              {displayText || <span className="text-gray-400">No draft yet.</span>}
              {streaming && <span className="inline-block w-1 h-4 bg-cyan-500 ml-0.5 animate-pulse align-middle" />}
            </div>
          )}
        </div>

        {/* Action result */}
        {actionResult && (
          <p className={`text-sm ${actionResult.ok ? "text-emerald-500" : "text-red-500"}`}>
            {actionResult.message}
          </p>
        )}

        {/* Action buttons */}
        {isPending && !streaming && displayText && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleApprove}
              disabled={approving}
              className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-sm px-5 py-2 rounded-lg transition-colors"
            >
              {approving ? "Sending..." : "Approve & Send"}
            </button>
            <button
              onClick={handleDiscard}
              className="border border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 text-sm px-5 py-2 rounded-lg transition-colors"
            >
              Discard
            </button>
          </div>
        )}
        {ticket.status === "sent" && (
          <div className="flex items-center gap-4">
            {draft?.sent_at && (
              <p className="text-xs text-emerald-500">
                Sent {new Date(draft.sent_at).toLocaleString()}
              </p>
            )}
            <button
              onClick={handleReset}
              disabled={resetting}
              className="text-xs text-gray-400 hover:text-cyan-500 disabled:opacity-50 transition-colors"
            >
              {resetting ? "Resetting..." : "Reset demo"}
            </button>
          </div>
        )}
      </div>

    </div>
  );
}
