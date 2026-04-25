"""Sample workflows seeded into ~/.reasonflow/workflows/ on first launch."""

from __future__ import annotations

import json
from pathlib import Path


SAMPLE_OLLAMA = {
    "name": "ollama_summarize_demo",
    "graph": {
        "nodes": [
            {
                "id": "n1",
                "type": "code",
                "position": {"x": 80, "y": 80},
                "data": {
                    "name": "prepare_text",
                    "code": (
                        "text = state.get('text') or "
                        "'ReasonFlow is an SDK-first agent orchestration framework. "
                        "Pipelines are built as DAGs of nodes connected with the >> operator. "
                        "It supports LLM, code, decision, and MCP nodes, runs on local Ollama "
                        "or cloud providers, and tracks cost and tokens automatically.'\n"
                        "return {'text': text}"
                    ),
                },
            },
            {
                "id": "n2",
                "type": "llm",
                "position": {"x": 80, "y": 240},
                "data": {
                    "name": "summarize",
                    "model": "ollama/gemma4:latest",
                    "prompt": (
                        "You are a concise summarizer. The user message is a JSON object with a "
                        "'text' field. Write a one-sentence summary. Reply with JSON: "
                        "{\"summary\": \"...\"}"
                    ),
                    "temperature": 0.3,
                },
            },
            {
                "id": "n3",
                "type": "llm",
                "position": {"x": 80, "y": 420},
                "data": {
                    "name": "tagline",
                    "model": "ollama/gemma4:latest",
                    "prompt": (
                        "You are a copywriter. Given JSON with a 'summary', write a punchy 6-word "
                        "tagline. Reply with JSON: {\"tagline\": \"...\"}"
                    ),
                    "temperature": 0.8,
                },
            },
            {
                "id": "n4",
                "type": "code",
                "position": {"x": 80, "y": 600},
                "data": {
                    "name": "format_output",
                    "code": (
                        "return {'result': {\n"
                        "    'summary': state.get('summary'),\n"
                        "    'tagline': state.get('tagline'),\n"
                        "}}"
                    ),
                },
            },
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n4"},
        ],
    },
}


from reasonflow.server.example_seeds import EXAMPLE_SEEDS

SAMPLES = [SAMPLE_OLLAMA, *EXAMPLE_SEEDS]


def seed_samples(workflow_dir: Path) -> None:
    """Write sample workflows if they don't already exist. Never overwrites."""
    workflow_dir.mkdir(parents=True, exist_ok=True)
    for sample in SAMPLES:
        path = workflow_dir / f"{sample['name']}.json"
        if path.exists():
            continue
        path.write_text(json.dumps(sample, indent=2))
