# SupportDesk

[![CI](https://github.com/eholt723/supportdesk/actions/workflows/ci.yml/badge.svg)](https://github.com/eholt723/supportdesk/actions/workflows/ci.yml)

AI-powered customer support automation. A webhook fires when a customer submits a ticket. The backend classifies it, searches a vector knowledge base for relevant documentation, and drafts a grounded reply — all before a human agent opens the ticket. The agent reviews, edits if needed, and approves. The reply goes out via Resend. Every pipeline stage is logged and broadcast to the live event dashboard in real time.

## Architecture

```
Customer /submit form
        │
        ▼ POST /api/webhook/ticket
        │ HMAC-SHA256 verified
        │ timestamp replay protection
        ▼
┌───────────────────────────────────────────────┐
│              Async Pipeline                   │
│                                               │
│  ┌─────────┐    ┌────────┐   ┌─────────────┐  │
│  │ Classify│──▶│ Search │──▶│    Draft    │  │
│  │  Groq   │    │pgvector│   │ Groq + RAG  │  │
│  └─────────┘    └────────┘   └──────┬──────┘  │
│                                    │ SSE      │
└────────────────────────────────────┼──────────┘
                                     │
                    ┌────────────────▼──────────────┐
                    │         Agent Dashboard       │
                    │  WebSocket event log  │ Draft │
                    │  Ticket queue         │Sources│
                    └────────────────┬──────────────┘
                                     │ Approve
                                     ▼
                               Resend email
                               to customer
```

**Classify** — Groq LLM reads the ticket and outputs `{type, urgency, confidence}`.
**Search** — fastembed encodes the ticket; pgvector returns the top 3 matching KB chunks by cosine similarity.
**Draft** — Groq LLM generates a response grounded in the retrieved passages. Tokens stream via SSE.
**Approve** — Agent reviews the draft and sources, edits if needed, clicks Approve. Resend delivers the reply.

## Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI, asyncio |
| LLM | Groq (llama-3.3-70b-versatile) |
| Embeddings | fastembed (BAAI/bge-small-en-v1.5) |
| Vector search | pgvector (cosine similarity) |
| Database | PostgreSQL on Neon |
| Email | Resend |
| Real-time | SSE (draft streaming), WebSocket (event log) |
| Frontend | React, Vite, Tailwind CSS |
| Hosting | Hugging Face Spaces (Docker) |
| CI | GitHub Actions |

## Pages

| Route | Description |
|---|---|
| `/` | Agent dashboard — ticket queue, stat cards, live WebSocket event log |
| `/ticket/:id` | Ticket detail — pipeline stages, RAG sources, streaming draft, approve/edit/discard |
| `/kb` | Knowledge base — view documents and chunks, upload new `.txt` files |
| `/submit` | Public ticket submission form (no login required) |
| `/about` | Project showcase — pipeline walkthrough, tech stack, GitHub link |

## Running Locally

### Prerequisites

- Python 3.12
- Node 20
- A [Neon](https://neon.tech) PostgreSQL database with pgvector enabled
- A [Groq](https://console.groq.com) API key
- A [Resend](https://resend.com) API key

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in DATABASE_URL, WEBHOOK_SECRET, GROQ_API_KEY, RESEND_API_KEY

# Run migrations and seed demo data
python -m migrations.run_migrations

# Ingest Vela knowledge base
python -m scripts.ingest_kb

# Start API server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env
# Set VITE_WEBHOOK_SECRET to the same value as backend WEBHOOK_SECRET
# Leave VITE_API_URL empty — Vite proxies /api to :8000 in dev

npm run dev
# Open http://localhost:5173
```

### Generate a webhook secret

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Run tests

```bash
cd backend
pytest
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `WEBHOOK_SECRET` | Shared HMAC secret for webhook signature verification |
| `GROQ_API_KEY` | Groq API key |
| `RESEND_API_KEY` | Resend API key |
| `RESEND_FROM_EMAIL` | From address (default: `supportdesk@ericholt.dev`) |

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `VITE_API_URL` | API base URL (empty in dev — Vite proxies to `:8000`) |
| `VITE_WEBHOOK_SECRET` | Same as backend `WEBHOOK_SECRET` — used by `/submit` form |

## Docker

```bash
docker build \
  --build-arg VITE_WEBHOOK_SECRET=your-secret \
  -t supportdesk .

docker run -p 7860:7860 \
  -e DATABASE_URL=... \
  -e WEBHOOK_SECRET=... \
  -e GROQ_API_KEY=... \
  -e RESEND_API_KEY=... \
  supportdesk
```

## Demo Tickets

Four pre-loaded tickets are visible in the dashboard immediately — no setup required:

1. **Billing / high urgency** — customer being charged after cancellation attempt
2. **Technical / high urgency** — CSV export broken after a platform update
3. **Feature request / low urgency** — asking whether API access is included on Pro
4. **Escalation / high urgency** — three unanswered support requests, threatening chargeback

Each is pre-classified, pre-drafted with RAG-grounded responses, and ready to demonstrate the full agent workflow.
