"""FastAPI app exposing the ReasonFlow visual builder."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from reasonflow.dag import TRACE_DIR
from reasonflow.server.builder import GraphError, build_dag, validate_graph
from reasonflow.server.providers import (
    list_ollama_models,
    list_providers,
    test_model,
)
from reasonflow.server.samples import seed_samples


WORKFLOW_DIR = Path.home() / ".reasonflow" / "workflows"
WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
seed_samples(WORKFLOW_DIR)


# ---------- node-type catalog (drives the inspector forms) ----------

NODE_TYPES = [
    {
        "type": "llm",
        "label": "LLM",
        "color": "#a855f7",
        "fields": [
            {"key": "name", "label": "Name", "kind": "text", "required": True},
            {"key": "model", "label": "Model", "kind": "model"},
            {"key": "prompt", "label": "Prompt (system)", "kind": "textarea",
             "placeholder": "You are a helpful assistant. State is provided as JSON."},
            {"key": "temperature", "label": "Temperature", "kind": "number", "default": 0.7},
        ],
    },
    {
        "type": "code",
        "label": "Code",
        "color": "#22c55e",
        "fields": [
            {"key": "name", "label": "Name", "kind": "text", "required": True},
            {"key": "code", "label": "Python (function body, receives `state`)",
             "kind": "code",
             "placeholder": "return {'upper': state['text'].upper()}"},
        ],
    },
    {
        "type": "decision",
        "label": "Decision",
        "color": "#f59e0b",
        "fields": [
            {"key": "name", "label": "Name", "kind": "text", "required": True},
            {"key": "code", "label": "Python — return 'next' or a node name",
             "kind": "code",
             "placeholder": "if state.get('score', 0) > 0.8:\n    return 'next'\nreturn 'retry_node'"},
        ],
    },
]


# ---------- request models ----------

class GraphPayload(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class RunPayload(BaseModel):
    graph: GraphPayload
    inputs: dict[str, Any] = {}
    name: str = "ui-pipeline"
    budget: str | None = None


class WorkflowPayload(BaseModel):
    name: str
    graph: GraphPayload


class TestModelPayload(BaseModel):
    model: str


# ---------- run registry (in-memory event queues per run_id) ----------

_runs: dict[str, asyncio.Queue] = {}
_results: dict[str, dict[str, Any]] = {}


def create_app(static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="ReasonFlow Builder")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/node-types")
    def node_types():
        return NODE_TYPES

    @app.get("/api/providers")
    async def providers():
        provs = list_providers()
        # populate ollama models
        for p in provs:
            if p["id"] == "ollama":
                p["models"] = await list_ollama_models()
        return provs

    @app.post("/api/providers/test")
    async def test_provider(payload: TestModelPayload):
        return await test_model(payload.model)

    @app.post("/api/validate")
    def validate(payload: GraphPayload):
        return validate_graph(payload.model_dump())

    @app.post("/api/run")
    async def run(payload: RunPayload):
        run_id = uuid.uuid4().hex[:12]
        queue: asyncio.Queue = asyncio.Queue()
        _runs[run_id] = queue

        loop = asyncio.get_event_loop()

        def on_span(event: str, data: dict[str, Any]) -> None:
            # Called from inside DAG execution (same loop)
            try:
                queue.put_nowait({"event": event, **data})
            except Exception:
                pass

        try:
            dag = build_dag(
                payload.graph.model_dump(),
                name=payload.name,
                budget=payload.budget,
                on_span=on_span,
            )
        except GraphError as e:
            raise HTTPException(status_code=400, detail=str(e))

        async def _execute():
            try:
                result = await dag.run_async(**payload.inputs)
                _results[run_id] = {
                    "success": result.success,
                    "state": _safe_json(result.state),
                    "total_cost": result.total_cost,
                    "tokens": result.tokens,
                    "error": result.error,
                    "trace": result.trace.to_dict(),
                }
                await queue.put({"event": "done", **_results[run_id]})
            except Exception as e:
                _results[run_id] = {"success": False, "error": str(e)}
                await queue.put({"event": "error", "error": str(e)})
            finally:
                await queue.put(None)  # sentinel

        loop.create_task(_execute())
        return {"run_id": run_id}

    @app.get("/api/run/{run_id}/stream")
    async def stream(run_id: str, request: Request):
        if run_id not in _runs:
            raise HTTPException(status_code=404, detail="Unknown run_id")
        queue = _runs[run_id]

        async def gen():
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    item = await queue.get()
                    if item is None:
                        break
                    yield f"data: {json.dumps(item, default=str)}\n\n"
            finally:
                _runs.pop(run_id, None)

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/run/{run_id}/result")
    def result(run_id: str):
        if run_id not in _results:
            raise HTTPException(status_code=404, detail="No result yet")
        return _results[run_id]

    # ---- workflow persistence ----
    @app.get("/api/workflows")
    def list_workflows():
        out = []
        for f in sorted(WORKFLOW_DIR.glob("*.json")):
            out.append({"name": f.stem, "modified": f.stat().st_mtime})
        return out

    @app.get("/api/workflows/{name}")
    def get_workflow(name: str):
        path = WORKFLOW_DIR / f"{_safe_filename(name)}.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Not found")
        return json.loads(path.read_text())

    @app.post("/api/workflows")
    def save_workflow(payload: WorkflowPayload):
        path = WORKFLOW_DIR / f"{_safe_filename(payload.name)}.json"
        path.write_text(json.dumps({
            "name": payload.name,
            "graph": payload.graph.model_dump(),
        }, indent=2))
        return {"ok": True, "path": str(path)}

    @app.delete("/api/workflows/{name}")
    def delete_workflow(name: str):
        path = WORKFLOW_DIR / f"{_safe_filename(name)}.json"
        if path.exists():
            path.unlink()
        return {"ok": True}

    # ---- traces ----
    @app.get("/api/traces")
    def list_traces():
        if not TRACE_DIR.exists():
            return []
        out = []
        for f in sorted(TRACE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
            out.append({"file": f.name, "modified": f.stat().st_mtime})
        return out

    @app.get("/api/traces/{name}")
    def get_trace(name: str):
        path = TRACE_DIR / _safe_filename(name)
        if not path.exists() or path.suffix != ".json":
            raise HTTPException(status_code=404, detail="Not found")
        return json.loads(path.read_text())

    # ---- static UI ----
    if static_dir and static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(static_dir / "index.html")

    return app


def _safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in "-_.") or "untitled"


def _safe_json(obj: Any) -> Any:
    """Make state JSON-serializable for the response."""
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return json.loads(json.dumps(obj, default=str))
