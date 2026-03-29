const BASE = import.meta.env.VITE_API_URL ?? "";

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
