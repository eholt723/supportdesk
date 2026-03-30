import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { get } from "../api";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export default function KB() {
  const [searchParams] = useSearchParams();
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const fileRef = useRef(null);
  const focusedChunkRef = useRef(null);

  useEffect(() => {
    if (!chunksLoading && selected && focusedChunkRef.current) {
      focusedChunkRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [chunksLoading]);

  function loadDocs() {
    return get("/api/kb").then(setDocs).catch(() => {});
  }

  useEffect(() => {
    const docParam = searchParams.get("doc");
    loadDocs().finally(() => {
      setLoading(false);
      if (docParam) {
        setSelected(docParam);
        setChunksLoading(true);
        get(`/api/kb/chunks?document_name=${encodeURIComponent(docParam)}&limit=100`)
          .then(setChunks)
          .catch(() => setChunks([]))
          .finally(() => setChunksLoading(false));
      }
    });
  }, []);

  function selectDoc(docName) {
    if (selected === docName) {
      setSelected(null);
      setChunks([]);
      return;
    }
    setSelected(docName);
    setChunksLoading(true);
    get(`/api/kb/chunks?document_name=${encodeURIComponent(docName)}&limit=100`)
      .then(setChunks)
      .catch(() => setChunks([]))
      .finally(() => setChunksLoading(false));
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const r = await fetch(`${API_BASE}/api/kb/upload`, { method: "POST", body: formData });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? `HTTP ${r.status}`);
      setUploadResult({ ok: true, message: `Uploaded "${data.document_name}" — ${data.chunks_stored} chunks` });
      await loadDocs();
    } catch (err) {
      setUploadResult({ ok: false, message: err.message });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handleDelete(docName) {
    if (!confirm(`Delete all chunks for "${docName}"?`)) return;
    try {
      const r = await fetch(`${API_BASE}/api/kb/${encodeURIComponent(docName)}`, { method: "DELETE" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      if (selected === docName) { setSelected(null); setChunks([]); }
      await loadDocs();
    } catch (err) {
      alert(err.message);
    }
  }

  const totalChunks = docs.reduce((s, d) => s + d.chunk_count, 0);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Knowledge Base</h1>
          <p className="text-sm text-gray-500">
            {loading ? "Loading..." : `${docs.length} documents · ${totalChunks} embedded chunks`}
          </p>
        </div>

        {/* Upload button */}
        <label className={`cursor-pointer bg-cyan-600 hover:bg-cyan-500 text-white text-sm px-4 py-2 rounded-lg transition-colors ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
          {uploading ? "Uploading..." : "Upload .txt"}
          <input
            ref={fileRef}
            type="file"
            accept=".txt"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>

      {uploadResult && (
        <p className={`text-sm ${uploadResult.ok ? "text-emerald-500" : "text-red-500"}`}>
          {uploadResult.message}
        </p>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
        {docs.length === 0 && !loading && (
          <p className="text-gray-500 text-sm p-6">No documents loaded.</p>
        )}
        {docs.map((doc) => (
          <div key={doc.document_name} ref={selected === doc.document_name ? focusedChunkRef : null}>
            <div className="flex items-center px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
              <button
                onClick={() => selectDoc(doc.document_name)}
                className="flex-1 flex items-center justify-between text-left"
              >
                <div className="space-y-0.5">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{doc.document_name}</p>
                  <p className="text-xs text-gray-500">{doc.chunk_count} chunks</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">
                    {new Date(doc.loaded_at).toLocaleDateString()}
                  </span>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform ${selected === doc.document_name ? "rotate-90" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </button>
              <button
                onClick={() => handleDelete(doc.document_name)}
                className="ml-4 text-xs text-gray-400 hover:text-red-500 transition-colors shrink-0"
                title="Delete document"
              >
                &#10005;
              </button>
            </div>

            {selected === doc.document_name && (
              <div className="px-5 pb-5 space-y-2">
                {chunksLoading ? (
                  <p className="text-sm text-gray-400">Loading chunks...</p>
                ) : (
                  chunks.map((chunk, i) => (
                    <div
                      key={chunk.id}
                      className="rounded-lg bg-gray-50 dark:bg-gray-950 border border-gray-100 dark:border-gray-800 p-3 space-y-1"
                    >
                      <p className="text-xs text-cyan-600 dark:text-cyan-400 font-mono">chunk {i + 1}</p>
                      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">{chunk.chunk_text}</p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
