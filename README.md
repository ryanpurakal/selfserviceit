# Trumid Self-Service IT Assistant

A minimal RAG-powered IT support prototype that **deflects common tickets** through intelligent self-service and **escalates the rest with full context preserved**.

> Built as a take-home / interview prototype. ~2 days of work, fully working locally with **no required API keys** (uses local sentence-transformers + a deterministic answer template by default; plug in Google Gemini or OpenAI for higher-quality synthesis).

---

## What it does

1. **Ingests IT documentation** (markdown/PDF) into a local ChromaDB vector store.
2. Lets an employee ask a question in a clean web UI.
3. Performs **semantic search** to find the most relevant chunks.
4. Uses an LLM (Gemini → OpenAI → template fallback) to **synthesize a cited answer** with a confidence score and related topics.
5. Asks **"Did this solve your problem?"** — `Yes` logs a deflection; `No` opens a mock ticket with the original question and the suggested solutions attached, so the IT engineer doesn't have to re-investigate.
6. Tracks deflection rate, time saved, top questions, and recent escalations on a live **analytics dashboard**.

---

## Architecture

```
┌──────────────────┐    /ask         ┌──────────────────────────────┐
│  React + Vite    │ ───────────────▶│ FastAPI                      │
│  (TypeScript,    │                 │  ├─ embeddings.py (ingest)   │
│   Tailwind v4)   │ ◀───────────────│  ├─ retrieval.py (semantic)  │
└──────────────────┘    answer +     │  ├─ llm.py (Gemini/OpenAI)   │
                        sources +    │  └─ analytics.py (JSON store)│
                        confidence   └──────────┬───────────────────┘
                                                │
                                                ▼
                                        ┌─────────────────┐
                                        │ ChromaDB (local)│
                                        │ all-MiniLM-L6   │
                                        └─────────────────┘
```

- **Vector store**: ChromaDB persistent client at `data/chroma_db/`.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` by default (free, local). Auto-switches to `text-embedding-3-small` if `OPENAI_API_KEY` is set.
- **Answer synthesis**: Gemini 2.5 Flash → GPT-4o-mini → deterministic template (so the demo always works, even offline). Get a Gemini key at <https://aistudio.google.com/apikey> — the free tier is generous enough for the demo.
- **Confidence**: weighted blend of the top-3 retrieval scores, mapped from Chroma L2 distance to a `[0,1]` similarity.
- **Analytics**: append-only JSON log at `data/analytics.json` with deflection rate, top questions, and recent escalations.

---

## Project structure

```
.
├── backend/
│   ├── main.py              FastAPI app + routes
│   ├── embeddings.py        Loaders, chunking, embedding backends
│   ├── retrieval.py         Semantic search + confidence scoring
│   ├── llm.py               Gemini → OpenAI → template fallback chain
│   ├── analytics.py         JSON-backed event store
│   ├── models.py            Pydantic request/response schemas
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   ├── api/client.ts                  Typed fetch wrapper
│   │   └── components/
│   │       ├── ChatInterface.tsx          Question → answer → feedback flow
│   │       ├── SourceCard.tsx             Citation card with relevance badge
│   │       ├── ConfidenceBar.tsx          Animated confidence indicator
│   │       └── AnalyticsDashboard.tsx     Live deflection metrics
│   ├── index.html
│   ├── package.json
│   ├── tsconfig*.json
│   ├── vite.config.ts
│   └── postcss.config.js
├── data/
│   ├── docs/                Sample Trumid IT docs (VPN, password, WiFi, etc.)
│   └── chroma_db/           Persistent vector store (gitignored)
└── README.md
```

---

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional - copy and add API keys
cp .env.example .env

uvicorn main:app --reload
```

The first time the server boots, it auto-ingests every file in `data/docs/`. To re-ingest later (after editing docs):

```bash
curl -X POST 'http://127.0.0.1:8000/embed?reset=true'
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to FastAPI on port 8000, so no CORS gymnastics during development.

---

## API

| Method | Path         | Description                                                                  |
| ------ | ------------ | ---------------------------------------------------------------------------- |
| GET    | `/health`    | Liveness check + indexed chunk count                                         |
| POST   | `/embed`     | (Re)ingest `data/docs/`. Pass `?reset=true` to drop the collection first    |
| POST   | `/ask`       | `{ "query": "..." }` → answer, sources, confidence, related topics           |
| POST   | `/feedback`  | `{ "question_id": "...", "deflected": true }` — logs deflection outcome     |
| POST   | `/escalate`  | Creates a mock ticket with the question + attempted solutions preserved      |
| GET    | `/analytics` | Returns deflection rate, time saved, top questions, recent escalations       |

OpenAPI docs live at `http://127.0.0.1:8000/docs` once the server is running.

---

## Demo script

1. **Show the problem** — "Trumid IT gets ~50 tickets/day. ~60% are password resets and VPN issues that the docs already answer."
2. **Successful deflection**
   - Type: `I can't connect to the VPN`
   - Show the answer rendered from `vpn.md` with **High confidence**, source citations, and related topics.
   - Click **Yes, I'm all set** → green "Ticket deflected" banner, +12 minutes saved.
3. **Failed deflection**
   - Type: `My laptop won't turn on`
   - Confidence is medium / low; the answer points to relevant troubleshooting but admits limitations.
   - Click **No, escalate to IT** → ticket `INC-XXXXXXXX` is created with the original question and the suggestions you saw, so the on-call engineer has full context.
4. **Analytics tab**
   - Deflection rate updates live (target: 40–50%).
   - "Top questions" reveals documentation gaps.
   - "Recent escalations" is the worklist for the IT team.
5. **Where this goes next**
   - Slack slash command (`/it`) with the same backend.
   - Real ticketing integration (Jira / ServiceNow create + link).
   - Feedback loop: when IT resolves an escalated ticket, the resolution becomes a new doc chunk automatically.
   - Per-team knowledge bases (Eng, Trading, Sales) via Chroma collections.
   - Multi-language support via the embedding model + Gemini.

---

## Design notes

- **Why a template fallback for synthesis?** The demo has to work even if the laptop is offline at the interview. The template stitches the top chunks into a structured Markdown answer with inline citations — not as good as Gemini, but good enough to show the flow end-to-end.
- **Why JSON for analytics?** Zero-infra. Swap `analytics.AnalyticsStore` for a SQLite or Postgres-backed implementation to scale; the interface is small.
- **Why MiniLM as default embedder?** ~80MB download, no API key, fast on CPU, and good enough for ~100 docs. For production with thousands of docs, switch to `text-embedding-3-small` (set `OPENAI_API_KEY`).
- **Chunking** uses `RecursiveCharacterTextSplitter` with markdown-aware separators (`\n## `, `\n### `, blank lines, etc.) so chunks tend to align with docs' natural sections.
- **Confidence** is a weighted blend of the top-3 retrieval scores (`0.6 / 0.25 / 0.15`). Single-chunk answers don't get artificially high scores; consistent agreement across chunks does.

---

## What was deliberately left out

These are flagged so the reviewer knows they're conscious choices, not oversights:

- **Auth / SSO** — would integrate with Okta in production; out of scope for a 2-day prototype.
- **Real ticketing system** — `INC-XXXX` is mock; the escalation payload already matches the shape Jira/ServiceNow webhooks expect.
- **Streaming responses** — the LLM call is synchronous. For the size of answers we're producing (~150 words) this feels instant; SSE streaming would be a one-evening add.
- **Per-user analytics & rate limiting** — the analytics module is keyed by question, not user.
- **Docker / deploy config** — local-first by design.
