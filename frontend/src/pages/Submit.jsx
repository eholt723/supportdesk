import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL ?? "";
const WEBHOOK_SECRET = import.meta.env.VITE_WEBHOOK_SECRET ?? "";

// HMAC-SHA256 using WebCrypto (available in all modern browsers)
async function hmacHex(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export default function Submit() {
  const [form, setForm] = useState({ email: "", subject: "", body: "" });
  const [status, setStatus] = useState(null); // null | "sending" | "ok" | "error"
  const [errorMsg, setErrorMsg] = useState("");

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("sending");

    const ts = Math.floor(Date.now() / 1000);
    const payload = JSON.stringify({
      email: form.email,
      subject: form.subject,
      body: form.body,
      timestamp: ts,
    });

    let sig = "";
    if (WEBHOOK_SECRET) {
      sig = await hmacHex(WEBHOOK_SECRET, `${ts}.${payload}`);
    }

    try {
      const r = await fetch(`${API_BASE}/api/webhook/ticket`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Webhook-Timestamp": String(ts),
          ...(sig ? { "X-Webhook-Signature": sig } : {}),
        },
        body: payload,
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${r.status}`);
      }
      setStatus("ok");
      setForm({ email: "", subject: "", body: "" });
    } catch (err) {
      setErrorMsg(err.message);
      setStatus("error");
    }
  }

  if (status === "ok") {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <div className="text-4xl">&#10003;</div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Ticket submitted</h2>
        <p className="text-sm text-gray-500">
          Our support team will review your request and reply to your email shortly.
        </p>
        <button
          onClick={() => setStatus(null)}
          className="text-sm text-cyan-600 dark:text-cyan-400 hover:underline"
        >
          Submit another ticket
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Contact Support</h1>
        <p className="text-sm text-gray-500">
          Describe your issue and a member of our team will get back to you.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={set("email")}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Subject</label>
          <input
            type="text"
            required
            value={form.subject}
            onChange={set("subject")}
            placeholder="Brief description of your issue"
            className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Message</label>
          <textarea
            required
            value={form.body}
            onChange={set("body")}
            placeholder="Please include as much detail as possible..."
            rows={6}
            className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
          />
        </div>

        {status === "error" && (
          <p className="text-sm text-red-500">{errorMsg}</p>
        )}

        <button
          type="submit"
          disabled={status === "sending"}
          className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
        >
          {status === "sending" ? "Submitting..." : "Submit Ticket"}
        </button>
      </form>

      <p className="text-xs text-gray-400 text-center">
        This form is for demo purposes. It connects directly to the SupportDesk backend.
      </p>
    </div>
  );
}
