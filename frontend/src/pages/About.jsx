import { Link } from "react-router-dom";

const PIPELINE_STEPS = [
  {
    num: "01",
    title: "Customer submits a ticket",
    desc: "A customer fills out the public form at /submit. Submission fires a POST to the backend webhook endpoint, signed with HMAC-SHA256 so only trusted sources are accepted.",
  },
  {
    num: "02",
    title: "Webhook verified and stored",
    desc: "The backend verifies the signature and timestamp (rejecting anything older than 5 minutes to block replay attacks), stores the raw event, and immediately returns 200. The pipeline runs asynchronously.",
  },
  {
    num: "03",
    title: "Classify",
    desc: "A Groq LLM reads the ticket subject and body and classifies it by type (billing, technical, feature request, escalation, general) and urgency (low, medium, high) — with a confidence score.",
  },
  {
    num: "04",
    title: "Search knowledge base",
    desc: "The ticket text is embedded using BAAI/bge-small-en-v1.5 (via fastembed). pgvector performs a cosine similarity search against the Vela documentation corpus and returns the top 3 matching passages.",
  },
  {
    num: "05",
    title: "Draft a grounded response",
    desc: "The retrieved passages are injected as context into a Groq LLM prompt. The model drafts a support reply grounded in the actual documentation — not hallucinated. Tokens stream to the agent UI in real time via SSE.",
  },
  {
    num: "06",
    title: "Human review and approval",
    desc: "A support agent sees the draft, the sources it was grounded in, and the pipeline timing. They can edit the text, then click Approve. The reply is delivered to the customer via Resend.",
  },
  {
    num: "07",
    title: "Full audit trail",
    desc: "Every step is logged: webhook events, pipeline stage timing, draft text, source passages used, who approved, and delivery status. Nothing disappears.",
  },
];

const USE_CASES = [
  {
    title: "SaaS Companies",
    desc: "Handle high ticket volume without growing your support team. SupportDesk drafts grounded replies from your own docs before an agent ever opens the ticket.",
  },
  {
    title: "E-commerce & Retail",
    desc: "Automatically draft answers to shipping delays, return policies, and billing disputes — pulled from your actual policy documents, not hallucinated.",
  },
  {
    title: "Financial Services & Fintech",
    desc: "Surface the right policy or compliance language before an agent responds. Every draft cites the source it was grounded in, so nothing gets made up.",
  },
  {
    title: "Healthcare & Insurance",
    desc: "Give agents a consistent, policy-grounded starting point across every support request — reducing variation and keeping responses aligned with what you've documented.",
  },
  {
    title: "Internal IT Help Desks",
    desc: "Auto-triage employee requests and draft answers from internal runbooks. Agents review and approve; the repetitive first draft is already done.",
  },
  {
    title: "Any Team Drowning in Repetitive Tickets",
    desc: "If more than half your tickets ask the same questions, SupportDesk can draft the answer from your knowledge base and put a human in the loop only for final sign-off.",
  },
];

const ACHIEVEMENTS = [
  "Webhook ingestion with HMAC-SHA256 signature verification and 5-minute replay protection",
  "Three-stage async pipeline: classify, RAG search, and LLM draft — each stage timed and logged",
  "RAG grounding using pgvector cosine similarity search — responses cite real documentation",
  "Streaming LLM output word-by-word to the agent UI via Server-Sent Events",
  "Human-in-the-loop approval: agent can read, edit, approve, or discard each draft",
  "Email delivery via Resend with delivery status logged per ticket",
  "Pre-loaded demo tickets with pre-classified types, urgencies, and RAG-grounded drafts",
  "Live event dashboard via WebSocket — every pipeline stage appears as it happens",
  "Full audit trail: webhook events, pipeline runs, drafts, sources, approvals, and delivery logs",
  "Deployed as a Docker container on Hugging Face Spaces",
];

const STACK = [
  { name: "Python + FastAPI", role: "Backend API and async pipeline" },
  { name: "Groq", role: "LLM classification and draft generation" },
  { name: "pgvector", role: "Vector similarity search" },
  { name: "fastembed", role: "Local embedding (BAAI/bge-small-en-v1.5)" },
  { name: "PostgreSQL / Neon", role: "All persistent storage" },
  { name: "Resend", role: "Transactional email delivery" },
  { name: "React + Vite", role: "Agent dashboard frontend" },
  { name: "Tailwind CSS", role: "Styling" },
  { name: "Hugging Face Spaces", role: "Hosting (Docker)" },
  { name: "GitHub Actions", role: "CI on every push" },
];

export default function About() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12 space-y-16">

      {/* Hero */}
      <section className="space-y-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">About SupportDesk</h1>
        <p className="text-base text-gray-600 dark:text-gray-400 leading-relaxed">
          SupportDesk is an AI-powered customer support automation system. When a customer submits
          a ticket, the backend automatically classifies it, searches a vector knowledge base for
          relevant documentation, and drafts a grounded reply — all before a human agent ever opens
          the ticket. The agent reviews the draft, edits if needed, and approves with one click.
        </p>
        <p className="text-base text-gray-600 dark:text-gray-400 leading-relaxed">
          The project demonstrates event-driven webhook ingestion, retrieval-augmented generation,
          real-time streaming, and human-in-the-loop approval — end to end, in a single deployable
          application.
        </p>
      </section>

      {/* How It Works */}
      <section className="space-y-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">How It Works</h2>
        <div className="space-y-0">
          {PIPELINE_STEPS.map((step, i) => (
            <div key={step.num} className="flex gap-5">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 rounded-full bg-cyan-100 dark:bg-cyan-900/50 border border-cyan-400 dark:border-cyan-700 flex items-center justify-center text-xs font-mono text-cyan-700 dark:text-cyan-400 shrink-0">
                  {step.num}
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className="w-px flex-1 bg-gray-200 dark:bg-gray-800 my-1" />
                )}
              </div>
              <div className="pb-8">
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">{step.title}</div>
                <div className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{step.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Where This Gets Used */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Where This Gets Used</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          Any team that handles customer requests has the same problem: support agents spend most of their time writing the same answers over and over. SupportDesk drafts those answers automatically — grounded in your own documentation — so agents spend their time reviewing and approving, not typing from scratch.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {USE_CASES.map(({ title, desc }) => (
            <div key={title} className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
              <div className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-1">{title}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* What Was Built */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">What Was Built</h2>
        <ul className="space-y-2">
          {ACHIEVEMENTS.map((a) => (
            <li key={a} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
              <span className="text-cyan-500 mt-0.5 shrink-0">&#10003;</span>
              {a}
            </li>
          ))}
        </ul>
      </section>

      {/* Tech Stack */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Tech Stack</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {STACK.map((s) => (
            <div
              key={s.name}
              className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-3"
            >
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{s.name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{s.role}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Links */}
      <section className="flex gap-3">
        <Link
          to="/"
          className="bg-cyan-600 hover:bg-cyan-500 text-white text-sm px-5 py-2.5 rounded-lg transition-colors"
        >
          Try the App
        </Link>
        <a
          href="https://github.com/eholt723/supportdesk"
          target="_blank"
          rel="noreferrer"
          className="border border-gray-300 dark:border-gray-700 hover:border-gray-500 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 text-sm px-5 py-2.5 rounded-lg transition-colors"
        >
          View on GitHub
        </a>
      </section>

    </div>
  );
}
