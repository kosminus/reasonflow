import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactFlow, {
  Background, Controls, MiniMap,
  addEdge, applyEdgeChanges, applyNodeChanges,
  ReactFlowProvider, useReactFlow,
} from 'reactflow';

import CustomNode from './CustomNode';
import Inspector from './Inspector';
import { delJSON, getJSON, postJSON, streamRun } from './api';

const NODE_TYPES_RF = { llm: CustomNode, code: CustomNode, decision: CustomNode };
let _idSeq = 1;
const newId = () => `n${_idSeq++}`;

function Builder() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selected, setSelected] = useState(null);
  const [nodeTypes, setNodeTypes] = useState([]);
  const [providers, setProviders] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [workflowName, setWorkflowName] = useState('untitled');
  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState({ cost: 0, tokens_in: 0, tokens_out: 0 });
  const [result, setResult] = useState(null);
  const [toast, setToast] = useState(null);
  const [inputJson, setInputJson] = useState('{}');
  const wrapperRef = useRef(null);
  const rf = useReactFlow();

  // Load catalogs on mount
  useEffect(() => {
    getJSON('/api/node-types').then(setNodeTypes).catch(() => {});
    refreshProviders();
    refreshWorkflows();
  }, []);

  const refreshProviders = () => getJSON('/api/providers').then(setProviders).catch(() => {});
  const refreshWorkflows = () => getJSON('/api/workflows').then(setWorkflows).catch(() => {});

  const showToast = (msg, kind = '') => {
    setToast({ msg, kind });
    setTimeout(() => setToast(null), 3000);
  };

  const onNodesChange = useCallback((c) => setNodes(ns => applyNodeChanges(c, ns)), []);
  const onEdgesChange = useCallback((c) => setEdges(es => applyEdgeChanges(c, es)), []);
  const onConnect = useCallback((params) => setEdges(es => addEdge(params, es)), []);
  const onSelectionChange = useCallback(({ nodes }) => {
    setSelected(nodes?.[0] || null);
  }, []);

  // Drag-and-drop from palette
  const onDragOver = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; };
  const onDrop = (e) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('application/reasonflow-type');
    if (!type) return;
    const bounds = wrapperRef.current.getBoundingClientRect();
    const position = rf.project({
      x: e.clientX - bounds.left,
      y: e.clientY - bounds.top,
    });
    const def = nodeTypes.find(t => t.type === type);
    const data = { name: `${type}_${_idSeq}` };
    if (type === 'llm') {
      const ollama = providers.find(p => p.id === 'ollama');
      const ollamaDefault = ollama?.models?.find(m => m.includes('gemma4')) || ollama?.models?.[0];
      const firstCloud = providers.find(p => p.id !== 'ollama' && p.key_present && p.models?.length);
      data.model = ollamaDefault || firstCloud?.models?.[0] || 'ollama/gemma4:latest';
      data.prompt = '';
    }
    if (type === 'code') data.code = "return {}";
    if (type === 'decision') data.code = "return 'next'";
    setNodes(ns => ns.concat({ id: newId(), type, position, data }));
  };

  const updateNode = (next) => {
    setNodes(ns => ns.map(n => n.id === next.id ? { ...n, data: next.data } : n));
    setSelected(next);
  };

  const deleteNode = (id) => {
    setNodes(ns => ns.filter(n => n.id !== id));
    setEdges(es => es.filter(e => e.source !== id && e.target !== id));
    setSelected(null);
  };

  // ---- save / load ----
  const saveWorkflow = async () => {
    const name = prompt('Workflow name:', workflowName);
    if (!name) return;
    setWorkflowName(name);
    await postJSON('/api/workflows', {
      name,
      graph: { nodes: serializeNodes(nodes), edges: serializeEdges(edges) },
    });
    refreshWorkflows();
    showToast(`Saved "${name}"`, 'success');
  };

  const loadWorkflow = async (name) => {
    if (!name) return;
    const wf = await getJSON(`/api/workflows/${name}`);
    const g = wf.graph;
    // restore react-flow positions if present, else lay out
    setNodes(g.nodes.map((n, i) => ({
      id: n.id, type: n.type,
      position: n.position || { x: 100, y: i * 100 },
      data: n.data,
    })));
    setEdges(g.edges.map(e => ({ id: `e_${e.source}_${e.target}`, source: e.source, target: e.target })));
    setWorkflowName(name);
    // bump idSeq
    g.nodes.forEach(n => {
      const m = /^n(\d+)$/.exec(n.id);
      if (m) _idSeq = Math.max(_idSeq, parseInt(m[1]) + 1);
    });
    showToast(`Loaded "${name}"`, 'success');
  };

  // ---- run ----
  const runPipeline = async () => {
    let inputs = {};
    try { inputs = JSON.parse(inputJson || '{}'); }
    catch { return showToast('Inputs must be valid JSON', 'error'); }

    // clear previous run state
    setNodes(ns => ns.map(n => ({
      ...n, data: { ...n.data, _status: undefined, _cost: undefined, _duration_ms: undefined }
    })));
    setStats({ cost: 0, tokens_in: 0, tokens_out: 0 });
    setResult(null);
    setRunning(true);

    let totalCost = 0, tIn = 0, tOut = 0;
    try {
      const { run_id } = await postJSON('/api/run', {
        graph: { nodes: serializeNodes(nodes), edges: serializeEdges(edges) },
        inputs,
        name: workflowName,
      });
      const es = streamRun(run_id, (ev) => {
        if (ev.event === 'node_start') {
          setNodeStatus(ev.node, 'running');
        } else if (ev.event === 'node_end') {
          setNodeStatus(ev.node, 'done', { cost: ev.cost, duration_ms: ev.duration_ms });
          totalCost += ev.cost || 0; tIn += ev.tokens_in || 0; tOut += ev.tokens_out || 0;
          setStats({ cost: totalCost, tokens_in: tIn, tokens_out: tOut });
        } else if (ev.event === 'node_error') {
          setNodeStatus(ev.node, 'error');
        } else if (ev.event === 'done') {
          setResult(ev);
          setRunning(false);
          es.close();
        } else if (ev.event === 'error') {
          showToast(ev.error || 'Run failed', 'error');
          setRunning(false);
          es.close();
        }
      });
    } catch (e) {
      showToast(e.message, 'error');
      setRunning(false);
    }
  };

  const setNodeStatus = (nodeName, status, extra = {}) => {
    setNodes(ns => ns.map(n => {
      if (n.data.name !== nodeName) return n;
      return { ...n, data: { ...n.data, _status: status,
        _cost: extra.cost ?? n.data._cost,
        _duration_ms: extra.duration_ms ?? n.data._duration_ms } };
    }));
  };

  return (
    <div className="app">
      <div className="topbar">
        <h1>ReasonFlow</h1>
        <select value="" onChange={e => loadWorkflow(e.target.value)}>
          <option value="">Load workflow…</option>
          {workflows.map(w => <option key={w.name} value={w.name}>{w.name}</option>)}
        </select>
        <button onClick={saveWorkflow}>Save</button>
        <span className="spacer" />
        <input value={inputJson} onChange={e => setInputJson(e.target.value)}
               placeholder='Inputs (JSON), e.g. {"topic":"AI"}'
               style={{ width: 280, fontFamily: 'ui-monospace, Menlo, monospace' }} />
        <span className="stats">
          ${stats.cost.toFixed(4)} · {stats.tokens_in}+{stats.tokens_out} tok
        </span>
        <button className="primary" disabled={running || nodes.length === 0} onClick={runPipeline}>
          {running ? 'Running…' : '▶ Run'}
        </button>
      </div>

      <div className="main">
        <Palette nodeTypes={nodeTypes} />

        <div className="canvas" ref={wrapperRef} onDrop={onDrop} onDragOver={onDragOver}>
          <ReactFlow
            nodes={nodes} edges={edges}
            onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            onConnect={onConnect} onSelectionChange={onSelectionChange}
            nodeTypes={NODE_TYPES_RF}
            fitView
          >
            <Background color="#334155" gap={20} />
            <Controls />
            <MiniMap pannable zoomable maskColor="rgba(15,23,42,0.7)"
                     nodeColor={(n) => ({llm:'#a855f7', code:'#22c55e', decision:'#f59e0b'}[n.type] || '#64748b')} />
          </ReactFlow>
        </div>

        <Inspector node={selected} nodeTypes={nodeTypes} providers={providers}
                   onChange={updateNode} onDelete={deleteNode}
                   refreshProviders={refreshProviders} />
      </div>

      {result && <ResultDrawer result={result} onClose={() => setResult(null)} />}
      {toast && <div className={`toast ${toast.kind}`}>{toast.msg}</div>}
    </div>
  );
}

function Palette({ nodeTypes }) {
  return (
    <aside className="palette">
      <h3>Nodes</h3>
      {nodeTypes.map(t => (
        <div key={t.type} className="palette-item"
             style={{ borderLeftColor: t.color }}
             draggable
             onDragStart={(e) => {
               e.dataTransfer.setData('application/reasonflow-type', t.type);
               e.dataTransfer.effectAllowed = 'move';
             }}>
          {t.label}
        </div>
      ))}
      <div style={{ marginTop: 24, fontSize: 11, color: '#64748b' }}>
        Drag a node onto the canvas. Connect by dragging from the bottom handle to another node's top handle.
      </div>
    </aside>
  );
}

function ResultDrawer({ result, onClose }) {
  return (
    <div className="drawer">
      <button className="close" onClick={onClose}>×</button>
      <h3>{result.success ? 'Run complete' : 'Run failed'}
        {' '}<span style={{ color: '#94a3b8', fontWeight: 400 }}>
          {result.total_cost} · {result.tokens?.input}+{result.tokens?.output} tok
        </span>
      </h3>
      {result.error && <div className="err">{result.error}</div>}
      <pre>{JSON.stringify(stripUnderscores(result.state || {}), null, 2)}</pre>
    </div>
  );
}

function stripUnderscores(o) {
  if (!o || typeof o !== 'object') return o;
  return Object.fromEntries(Object.entries(o).filter(([k]) => !k.startsWith('_')));
}

function serializeNodes(nodes) {
  return nodes.map(n => ({
    id: n.id, type: n.type, position: n.position,
    data: Object.fromEntries(Object.entries(n.data).filter(([k]) => !k.startsWith('_'))),
  }));
}
function serializeEdges(edges) {
  return edges.map(e => ({ source: e.source, target: e.target }));
}

export default function App() {
  return (
    <ReactFlowProvider>
      <Builder />
    </ReactFlowProvider>
  );
}
