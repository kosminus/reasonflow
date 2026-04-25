"""Translate a JSON graph from the UI into a runnable DAG.

Graph format (from React Flow):
    {
      "nodes": [
        {"id": "n1", "type": "llm", "data": {"name": "summarize",
          "model": "claude-sonnet-4-6", "prompt": "Summarize the input.",
          "temperature": 0.7}},
        {"id": "n2", "type": "code", "data": {"name": "uppercase",
          "code": "return {'upper': state['summary'].upper()}"}},
        ...
      ],
      "edges": [{"source": "n1", "target": "n2"}, ...]
    }

We support graphs that decompose into a chain of nodes and parallel groups
(diamonds: one source fan-out, all branches converge on one sink).
"""

from __future__ import annotations

import json
from typing import Any

from reasonflow.dag import DAG
from reasonflow.nodes.base import BaseNode, parallel
from reasonflow.nodes.code import CodeNode
from reasonflow.nodes.decision import DecisionNode
from reasonflow.nodes.llm import LLMNode


class GraphError(ValueError):
    """Raised when a UI graph cannot be translated into a DAG."""


# ---------- node factories ----------

def _safe_name(raw: str, fallback: str) -> str:
    name = (raw or fallback).strip().replace(" ", "_")
    return name or fallback


def _build_llm(node_id: str, data: dict[str, Any]) -> BaseNode:
    name = _safe_name(data.get("name"), node_id)
    model = data.get("model") or "claude-sonnet-4-6"
    prompt = data.get("prompt") or ""
    temperature = data.get("temperature")  # noqa: kept for future use

    def _fn(state):
        return None

    _fn.__name__ = name
    _fn.__doc__ = prompt
    return LLMNode(model=model)(_fn)


def _build_code(node_id: str, data: dict[str, Any]) -> BaseNode:
    name = _safe_name(data.get("name"), node_id)
    code = data.get("code") or "return {}"

    # Compile a function body — user code runs in the server process.
    # This is a single-user local dev tool; documented in README.
    src = "def _user_fn(state):\n"
    for line in code.splitlines() or ["return {}"]:
        src += f"    {line}\n"

    ns: dict[str, Any] = {}
    try:
        exec(src, ns)
    except SyntaxError as e:
        raise GraphError(f"CodeNode '{name}' has a syntax error: {e}")

    fn = ns["_user_fn"]
    fn.__name__ = name
    return CodeNode(fn)


def _build_decision(node_id: str, data: dict[str, Any]) -> BaseNode:
    name = _safe_name(data.get("name"), node_id)
    code = data.get("code") or "return 'next'"

    src = "def _user_fn(state):\n"
    for line in code.splitlines() or ["return 'next'"]:
        src += f"    {line}\n"

    ns: dict[str, Any] = {}
    try:
        exec(src, ns)
    except SyntaxError as e:
        raise GraphError(f"DecisionNode '{name}' has a syntax error: {e}")

    fn = ns["_user_fn"]
    fn.__name__ = name
    return DecisionNode(fn)


_FACTORIES = {
    "llm": _build_llm,
    "code": _build_code,
    "decision": _build_decision,
}


# ---------- topology ----------

def _build_adjacency(graph: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Return (out_edges, in_edges) keyed by node id."""
    out: dict[str, list[str]] = {n["id"]: [] for n in graph["nodes"]}
    inn: dict[str, list[str]] = {n["id"]: [] for n in graph["nodes"]}
    ids = set(out.keys())
    for e in graph.get("edges", []):
        s, t = e["source"], e["target"]
        if s not in ids or t not in ids:
            raise GraphError(f"Edge references unknown node: {e}")
        out[s].append(t)
        inn[t].append(s)
    return out, inn


def _detect_cycle(out_edges: dict[str, list[str]]) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in out_edges}

    def visit(n: str) -> bool:
        color[n] = GRAY
        for m in out_edges[n]:
            if color[m] == GRAY:
                return True
            if color[m] == WHITE and visit(m):
                return True
        color[n] = BLACK
        return False

    return any(color[n] == WHITE and visit(n) for n in out_edges)


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Return {ok: bool, errors: [str]}. Does not build."""
    errors: list[str] = []
    nodes = graph.get("nodes", [])
    if not nodes:
        return {"ok": False, "errors": ["Graph is empty."]}

    seen_ids = set()
    seen_names = set()
    for n in nodes:
        if "id" not in n:
            errors.append(f"Node missing id: {n}")
            continue
        if n["id"] in seen_ids:
            errors.append(f"Duplicate node id: {n['id']}")
        seen_ids.add(n["id"])
        if n.get("type") not in _FACTORIES:
            errors.append(f"Node {n['id']} has unknown type: {n.get('type')!r}")
        nm = (n.get("data", {}).get("name") or "").strip()
        if nm:
            if nm in seen_names:
                errors.append(f"Duplicate node name: {nm!r}")
            seen_names.add(nm)

    if errors:
        return {"ok": False, "errors": errors}

    try:
        out_edges, in_edges = _build_adjacency(graph)
    except GraphError as e:
        return {"ok": False, "errors": [str(e)]}

    sources = [n for n, parents in in_edges.items() if not parents]
    sinks = [n for n, kids in out_edges.items() if not kids]

    if len(sources) != 1:
        errors.append(f"Graph must have exactly one source node (found {len(sources)}).")
    if len(sinks) != 1:
        errors.append(f"Graph must have exactly one sink node (found {len(sinks)}).")
    if _detect_cycle(out_edges):
        errors.append("Graph contains a cycle.")

    return {"ok": not errors, "errors": errors}


def _linearize(graph: dict[str, Any]) -> list[Any]:
    """Decompose graph into [BaseNode | ParallelGroup, ...].

    Walks from the source. A node with multiple out-edges that all converge
    on a single descendant becomes a ParallelGroup.
    """
    out_edges, in_edges = _build_adjacency(graph)
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}

    sources = [n for n, parents in in_edges.items() if not parents]
    if len(sources) != 1:
        raise GraphError("Graph must have exactly one source.")

    items: list[Any] = []
    cursor = sources[0]
    visited: set[str] = set()

    while cursor is not None:
        if cursor in visited:
            raise GraphError(f"Unexpected revisit of node {cursor}.")
        visited.add(cursor)
        children = out_edges[cursor]

        # Build the node for the cursor itself
        cur_def = nodes_by_id[cursor]
        items.append(_build_node(cur_def))

        if not children:
            cursor = None
            break

        if len(children) == 1:
            child = children[0]
            # if child has multiple parents and all parents are us → ok (linear)
            # if child has multiple parents but they're outside our path, that's a join we don't support v1
            if len(in_edges[child]) != 1:
                raise GraphError(
                    f"Node {child!r} has multiple parents but is not the join of a parallel branch from {cursor!r}."
                )
            cursor = child
        else:
            # Fan-out: children must all converge on a single join node
            joins = {tuple(sorted(_descendants_to_join(c, out_edges))) for c in children}
            # Each child must have exactly one outgoing edge to the same join node
            child_targets = []
            for c in children:
                ct = out_edges[c]
                if len(ct) != 1:
                    raise GraphError(
                        f"Parallel branch starting at {c!r} must have exactly one downstream edge."
                    )
                if in_edges[c] != [cursor]:
                    raise GraphError(
                        f"Parallel branch {c!r} must only be entered from {cursor!r}."
                    )
                child_targets.append(ct[0])
            if len(set(child_targets)) != 1:
                raise GraphError(
                    f"Parallel branches from {cursor!r} must converge on a single node."
                )
            join_id = child_targets[0]
            if sorted(in_edges[join_id]) != sorted(children):
                raise GraphError(
                    f"Join node {join_id!r} must have exactly the parallel branches as parents."
                )

            # Build each branch node and group them
            branch_nodes = []
            for c in children:
                visited.add(c)
                branch_nodes.append(_build_node(nodes_by_id[c]))
            items.append(parallel(*branch_nodes))
            cursor = join_id

    return items


def _descendants_to_join(start: str, out_edges: dict[str, list[str]]) -> set[str]:
    """Used only for diagnostics — returns reachable nodes from start."""
    seen = set()
    stack = [start]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(out_edges.get(n, []))
    return seen


def _build_node(node_def: dict[str, Any]) -> BaseNode:
    factory = _FACTORIES.get(node_def["type"])
    if not factory:
        raise GraphError(f"Unknown node type: {node_def['type']!r}")
    return factory(node_def["id"], node_def.get("data", {}))


# ---------- public entry ----------

def build_dag(
    graph: dict[str, Any],
    *,
    name: str = "ui-pipeline",
    budget: str | None = None,
    on_span: Any = None,
) -> DAG:
    """Build a DAG from a UI graph. Raises GraphError on bad input."""
    v = validate_graph(graph)
    if not v["ok"]:
        raise GraphError("; ".join(v["errors"]))

    items = _linearize(graph)
    # Build a chain manually
    from reasonflow.nodes.base import NodeChain
    chain = NodeChain()
    for it in items:
        chain.add(it)

    dag = DAG(name=name, budget=budget)
    dag.connect(chain)
    if on_span is not None:
        dag._on_span = on_span  # consumed by patched DAG
    return dag
