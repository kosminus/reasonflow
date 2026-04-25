"""Tests for the UI graph → DAG translator."""

import pytest

from reasonflow.server.builder import GraphError, build_dag, validate_graph


def test_validate_empty():
    r = validate_graph({"nodes": [], "edges": []})
    assert not r["ok"]


def test_validate_linear_chain():
    g = {
        "nodes": [
            {"id": "a", "type": "code", "data": {"name": "a", "code": "return {'x': 1}"}},
            {"id": "b", "type": "code", "data": {"name": "b", "code": "return {'y': state['x'] + 1}"}},
        ],
        "edges": [{"source": "a", "target": "b"}],
    }
    r = validate_graph(g)
    assert r["ok"], r["errors"]


def test_validate_cycle_rejected():
    g = {
        "nodes": [
            {"id": "a", "type": "code", "data": {"name": "a", "code": "return {}"}},
            {"id": "b", "type": "code", "data": {"name": "b", "code": "return {}"}},
        ],
        "edges": [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "a"},
        ],
    }
    r = validate_graph(g)
    assert not r["ok"]


def test_validate_two_sources_rejected():
    g = {
        "nodes": [
            {"id": "a", "type": "code", "data": {"name": "a", "code": "return {}"}},
            {"id": "b", "type": "code", "data": {"name": "b", "code": "return {}"}},
            {"id": "c", "type": "code", "data": {"name": "c", "code": "return {}"}},
        ],
        "edges": [
            {"source": "a", "target": "c"},
            {"source": "b", "target": "c"},
        ],
    }
    r = validate_graph(g)
    # two sources, but c is the join — actually our rule says exactly 1 source.
    assert not r["ok"]


async def test_build_and_run_linear():
    g = {
        "nodes": [
            {"id": "a", "type": "code", "data": {"name": "a", "code": "return {'x': 10}"}},
            {"id": "b", "type": "code", "data": {"name": "b", "code": "return {'y': state['x'] * 2}"}},
        ],
        "edges": [{"source": "a", "target": "b"}],
    }
    dag = build_dag(g, name="test")
    result = await dag.run_async()
    assert result.success
    assert result.state["y"] == 20


async def test_build_and_run_parallel():
    g = {
        "nodes": [
            {"id": "src", "type": "code", "data": {"name": "src", "code": "return {'n': 5}"}},
            {"id": "a", "type": "code", "data": {"name": "branch_a", "code": "return {'a': state['n'] + 1}"}},
            {"id": "b", "type": "code", "data": {"name": "branch_b", "code": "return {'b': state['n'] * 2}"}},
            {"id": "join", "type": "code", "data": {"name": "join",
             "code": "return {'sum': state['a'] + state['b']}"}},
        ],
        "edges": [
            {"source": "src", "target": "a"},
            {"source": "src", "target": "b"},
            {"source": "a", "target": "join"},
            {"source": "b", "target": "join"},
        ],
    }
    dag = build_dag(g, name="test_par")
    result = await dag.run_async()
    assert result.success, result.error
    assert result.state["sum"] == 6 + 10  # (5+1) + (5*2)


async def test_emit_callback_fires():
    events = []
    g = {
        "nodes": [
            {"id": "a", "type": "code", "data": {"name": "a", "code": "return {'x': 1}"}},
        ],
        "edges": [],
    }
    dag = build_dag(g, on_span=lambda ev, payload: events.append(ev))
    result = await dag.run_async()
    assert result.success
    assert "node_start" in events
    assert "node_end" in events
