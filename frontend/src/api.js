const BASE = import.meta.env.VITE_API_URL ?? "";
const WEBHOOK_SECRET = import.meta.env.VITE_WEBHOOK_SECRET ?? "";

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

export async function submitTicket(email, subject, body) {
  const ts = Math.floor(Date.now() / 1000);
  const payload = JSON.stringify({ email, subject, body, timestamp: ts });
  let sig = "";
  if (WEBHOOK_SECRET) {
    sig = await hmacHex(WEBHOOK_SECRET, `${ts}.${payload}`);
  }
  const r = await fetch(`${BASE}/api/webhook/ticket`, {
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
  return r.json();
}

export async function get(path) {
  const r = await fetch(BASE + path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export function wsUrl(path) {
  const base = import.meta.env.VITE_API_URL ?? "";
  const ws = base.replace(/^http/, "ws");
  return ws + path;
}

export function sseUrl(path) {
  return (import.meta.env.VITE_API_URL ?? "") + path;
}
