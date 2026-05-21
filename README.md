# Trumid Self-Service Assistants

A minimal RAG-powered prototype with two assistants sharing one backend:

- **IT Support** — deflects common technical tickets (VPN, passwords, WiFi, access).
- **Trader Onboarding** — guides new traders on platform protocols, compliance, and tools.

Both use the same FastAPI + ChromaDB + sentence-transformers stack but search separate document collections. The UI has tabs to switch between them; analytics track deflections across both.

> Built as a take-home / interview prototype. Fully working locally with **no required API keys** (local sentence-transformers + deterministic answer template by default; plug in Google Gemini or OpenAI for higher-quality synthesis).

---

## What it does

1. **Ingests documentation** (markdown/PDF) into separate ChromaDB collections (`it_docs`, `onboarding_docs`).
2. Lets users ask questions in a tabbed web UI (IT Support vs Trader Onboarding).
3. Performs **semantic search** against the active collection.
4. Uses an LLM (Gemini → OpenAI → template fallback) to **synthesize a cited answer** with confidence and related topics.
5. Asks **"Did this solve your problem?"** — `Yes` logs a deflection; `No` opens a mock ticket with full context preserved.
6. Tracks deflection rate, time saved, top questions, and recent escalations on a shared **analytics dashboard**.

---

## Architecture

```
┌──────────────────┐    /ask         ┌──────────────────────────────┐
│  React + Vite    │  collection_name │ FastAPI                      │
│  TabNavigation   │ ───────────────▶│  ├─ embeddings.py (ingest)   │
│  ChatInterface   │ ◀───────────────│  ├─ retrieval.py (semantic)  │
│  (Tailwind v4)   │    answer +     │  ├─ llm.py (Gemini/OpenAI)   │
└──────────────────┘    sources +    │  └─ analytics.py (JSON store)│
                        confidence   └──────────┬───────────────────┘
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        ▼                                               ▼
                ┌─────────────────┐                         ┌─────────────────┐
                │ ChromaDB        │                         │ ChromaDB        │
                │ collection:     │                         │ collection:     │
                │ it_docs         │                         │ onboarding_docs │
                │ ← data/docs/it  │                         │ ← data/docs/    │
                │                 │                         │   onboarding    │
                └─────────────────┘                         └─────────────────┘
```

- **Vector store**: ChromaDB at `data/chroma_db/` with one collection per assistant.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` by default. Auto-switches to `text-embedding-3-small` if `OPENAI_API_KEY` is set.
- **Answer synthesis**: Gemini 2.5 Flash → GPT-4o-mini → deterministic template. Gemini key: <https://aistudio.google.com/apikey>
- **Confidence**: weighted blend of top-3 retrieval scores, mapped from Chroma L2 distance to `[0,1]`.
- **Analytics**: append-only JSON at `data/analytics.json` (shared across both tabs).

---

## Project structure

```
.
├── backend/
│   ├── main.py              FastAPI app, dual-collection ingest + /ask routing
│   ├── embeddings.py        Loaders, chunking, per-collection ingest
│   ├── retrieval.py         Semantic search (collection_name param)
│   ├── llm.py               Gemini → OpenAI → template fallback
│   ├── analytics.py         JSON-backed event store
│   ├── models.py            Pydantic schemas (Question.collection_name)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                        Ask / Analytics + assistant tabs
│   │   ├── api/client.ts
│   │   └── components/
│   │       ├── TabNavigation.tsx          IT Support vs Trader Onboarding
│   │       ├── ChatInterface.tsx          Q&A flow (collectionName prop)
│   │       ├── SourceCard.tsx
│   │       ├── ConfidenceBar.tsx
│   │       └── AnalyticsDashboard.tsx
│   └── vite.config.ts                     Proxies /api → :8000
├── data/
│   ├── docs/
│   │   ├── it/              VPN, password, WiFi, printing, etc.
│   │   └── onboarding/      Platform basics, compliance, tools, FAQ
│   └── chroma_db/           gitignored (`it_docs` + `onboarding_docs`)
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

# Optional — API keys for better answer synthesis
cp .env.example .env   # if present; else create .env manually

# Verify the venv is active (paths should be under backend/.venv/bin/)
which python3 uvicorn

uvicorn main:app --reload
```

If `uvicorn` is not found after `activate`, use the venv binary directly:

```bash
.venv/bin/uvicorn main:app --reload
```

On startup, the server auto-ingests `data/docs/it/` → `it_docs` and `data/docs/onboarding/` → `onboarding_docs` when each collection is empty.

Re-ingest after editing docs (both collections):

```bash
curl -X POST 'http://127.0.0.1:8000/embed?reset=true'
```

Re-ingest one collection only:

```bash
curl -X POST 'http://127.0.0.1:8000/embed?reset=true&collection_name=onboarding_docs'
```

Check indexed chunk counts:

```bash
curl http://127.0.0.1:8000/health
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Use **IT Support** or **Trader Onboarding** tabs at the top of the Ask view.

---

## API

| Method | Path         | Description |
| ------ | ------------ | ----------- |
| GET    | `/health`    | Status + per-collection chunk counts (`collections.it_docs`, `collections.onboarding_docs`) |
| POST   | `/embed`     | Ingest all collections, or one via `?collection_name=onboarding_docs`. Use `?reset=true` to drop and rebuild |
| POST   | `/ask`       | `{ "query": "...", "collection_name": "it_docs" }` — use `onboarding_docs` for trader onboarding |
| POST   | `/feedback`  | `{ "question_id": "...", "deflected": true }` |
| POST   | `/escalate`  | Mock ticket with question + attempted solutions |
| GET    | `/analytics` | Deflection metrics (both assistants) |

OpenAPI: http://127.0.0.1:8000/docs

**Collection names:** `it_docs` (default), `onboarding_docs`

---

## Demo script

### IT Support tab

1. **Problem** — "Trumid IT gets ~50 tickets/day; many are VPN/password issues the docs already answer."
2. **Deflection** — Ask: `I can't connect to the VPN` → high confidence, citations from `vpn.md` → **Yes, I'm all set**.
3. **Escalation** — Ask: `My laptop won't turn on` → lower confidence → **No, escalate to IT** → mock ticket with context.

### Trader Onboarding tab

1. Switch to **Trader Onboarding**.
2. Ask: `How do I execute my first trade?` or `What are RFQ and Swarms?` → answers from onboarding docs.
3. Ask: `What compliance checks run before a trade?` → citations from `compliance-basics.md`.

### Analytics

- Open the **Analytics** nav tab — deflection rate and top questions include activity from both assistants.

### Roadmap (not built)

- Slack slash command (`/it`, `/onboard`)
- Real ticketing (Jira / ServiceNow)
- Auto-ingest resolved tickets as new doc chunks
- Per-desk collections beyond IT + onboarding

---

## Design notes

- **Shared RAG backend, separate collections** — Same embedding model and ingest pipeline; `collection_name` on `/ask` selects the Chroma collection. Adding a third assistant is a new folder under `data/docs/` plus one line in `COLLECTION_SOURCES` in `main.py`.
- **Template fallback** — Works offline for demos; stitches top chunks with citations when no LLM key is set.
- **JSON analytics** — Zero-infra; one store for both tabs.
- **Chunking** — `RecursiveCharacterTextSplitter` with markdown-aware separators (`\n## `, etc.).

---

## What was deliberately left out

- **Auth / SSO** — Okta in production; out of scope here.
- **Real ticketing** — `INC-XXXX` is mock.
- **Streaming responses** — synchronous LLM calls.
- **Per-user analytics** — keyed by question, not user.
- **Docker / deploy** — local-first by design.
