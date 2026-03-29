import { useEffect, useState } from "react";
import { get } from "../api";

export default function KB() {
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [chunksLoading, setChunksLoading] = useState(false);

  useEffect(() => {
    get("/api/kb")
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false));
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

  const totalChunks = docs.reduce((s, d) => s + d.chunk_count, 0);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Knowledge Base</h1>
        <p className="text-sm text-gray-500">
          {loading ? "Loading..." : `${docs.length} documents · ${totalChunks} embedded chunks`}
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
        {docs.map((doc) => (
          <div key={doc.document_name}>
            <button
              onClick={() => selectDoc(doc.document_name)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors text-left"
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
