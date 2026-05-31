# song-recommendation-agent

**Multimodal music discovery agent** — turn text or image mood into a curated playlist with explanations and YouTube links.

End-to-end stack: **FastAPI** backend, **Next.js** frontend, **OpenAI API** (text + vision), **Brave Search**, and **Jina Reader** for web evidence. The main path is a **hand-orchestrated four-stage pipeline** (search-augmented), not vector RAG.

---

## Features

- **Text input** — natural-language requests (genre, mood, OST, era, etc.)
- **Image input** — upload a photo; vision model infers atmosphere and search intent
- **Web discovery** — Wikipedia / Reddit-style sources + Brave queries + page text via Jina Reader
- **Quality gate** — rule-based filtering (covers, remixes, etc.) + batched LLM verification
- **Structured API** — JSON responses for the frontend (`/recommend`, `/recommend/image`)

---

## Architecture

```
User (text or image)
        │
        ▼
┌───────────────────┐
│ 1. Perception     │  OpenAI API — intent JSON (search_goal, region, vocal_type, …)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 2. Discovery      │  Brave Search + Jina Reader → evidence → LLM song–artist clues
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 3. Decision       │  YouTube source search, hard filters, batched LLM validation
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 4. Generation     │  Final report + optional LLM blurbs for display
└─────────┬─────────┘
          ▼
   FastAPI → Next.js UI
```

| Stage | Module | Role |
|--------|--------|------|
| Perception | `agent/chains/perception.py` | Parse text or analyze image → shared `context` dict |
| Discovery | `agent/chains/discovery.py` | Fetch web evidence, extract candidate tracks |
| Decision | `agent/chains/decision.py` | Resolve links, filter noise, rank & dedupe |
| Generation | `agent/chains/generation.py` | Build user-facing recommendation text |

Entry point: `music_ai_agent.py` (`MusicAgent.recommend()`). HTTP layer: `main.py`.

---

## Tech stack

| Layer | Technologies |
|--------|----------------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| LLM | **OpenAI API** (chat + vision) via `agent/models.py` |
| Search / content | **Brave Search API**, **Jina Reader** (`https://r.jina.ai/…`) |
| Orchestration | Four-stage pipeline in `MusicAgent.recommend()`; `asyncio` for concurrent I/O in discovery |

---

## Prerequisites

Create `.env.local` in the project root:

```env
OPENAI_API_KEY=your_openai_key
BRAVE_API_KEY=your_brave_search_key
```

Brave is required for the main recommendation path (web discovery and YouTube source lookup). Without it, discovery may skip or degrade.

---

## Quick start

### Backend (port 8000)

```bash
cd song-recommendation-agent   # your clone directory
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start API (loads MusicAgent on startup)
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Or use `./start_api.sh` (creates/uses `venv` if configured).

- API docs: http://127.0.0.1:8000/docs  
- Health: root `/` returns 404 by design; use `/docs` or `POST /recommend`.

### Frontend (port 3000)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — ensure the backend is already running on port 8000.

> **Note:** A single recommendation can take **1–3+ minutes** (multiple Brave calls, Jina fetches, and several LLM requests). The UI shows a loading state while waiting.

---

## API

| Method | Path | Body |
|--------|------|------|
| `POST` | `/recommend` | `{ "user_input": "rock music from the 90s" }` |
| `POST` | `/recommend/image` | `multipart/form-data` field `image` (JPEG/PNG) |

Response shape: `success`, `search_goal`, `songs[]` (`title`, `artist`, `reason`, `link`, …).

---

## Project layout

```
├── music_ai_agent.py      # MusicAgent orchestrator
├── main.py                # FastAPI app
├── agent/
│   ├── chains/            # perception, discovery, decision, generation
│   ├── models.py          # OpenAI / ModelManager
│   ├── tools.py           # MusicSearchTool (Chroma, optional)
│   └── prompts/
├── external/
│   └── brave_search.py
├── database/
│   └── vector_store.py    # ChromaDB (optional path)
├── frontend/              # Next.js app
└── requirements.txt
```

---

## Optional: audio similarity (ChromaDB)

The repo also includes **SE-ResNet–style embeddings** and **ChromaDB** (`database/vector_store.py`, `agent/tools.py`) for genre / timbre-neighbor search. That path is **not** wired into `MusicAgent.recommend()` today; the live product path is **web search + LLM extraction** above.

---

## Known limitations

- **Label vs. video:** Displayed `artist` / `song` come from discovery clues; the YouTube URL is chosen separately from search results — titles can occasionally disagree with the linked video.
- **Topic drift:** Image mood (e.g. memorial / ambient) may still retrieve culturally associated rock/metal tracks from Wikipedia-heavy evidence.
- **Latency & quotas:** Brave free tier may rate-limit; long runs are expected on cold starts.

---

## Development

```bash
# Text smoke test (from repo root, with .env.local set)
python music_ai_agent.py
```

Frontend details: see `frontend/README.md`.

