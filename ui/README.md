# ReasonFlow UI

Visual builder for ReasonFlow pipelines — drag, drop, connect, run.

## Setup

Requires Node 18+ and the Python `[ui]` extra:

```bash
pip install -e ".[ui]"
cd ui
npm install
```

## Dev mode (auto-reload)

Two terminals:

```bash
# Terminal 1 — Python API (port 8765)
reasonflow ui

# Terminal 2 — Vite dev server (port 5173, proxies /api → 8765)
cd ui && npm run dev
```

Then open http://localhost:5173

## Production build

```bash
cd ui && npm run build      # outputs to src/reasonflow/server/static/
reasonflow ui                # serves the built UI at http://127.0.0.1:8765
```

## Provider configuration

The Inspector lets you pick **Claude / OpenAI / Gemini / Ollama** per LLM node.
Cloud providers need API keys in environment (`.env` works):

- `ANTHROPIC_API_KEY` for Claude
- `OPENAI_API_KEY` for OpenAI
- `GEMINI_API_KEY` for Gemini
- Ollama needs no key — pull models locally with `ollama pull llama3`

Use the **Test connection** button in the inspector to verify a model works
before running the pipeline.

## Security note

`CodeNode` and `DecisionNode` execute user-supplied Python in the server
process. The UI is intended for **single-user local dev** — do not expose
`reasonflow ui` on a network without an auth proxy.
