import { Handle, Position } from 'reactflow';

const COLORS = {
  llm: '#a855f7',
  code: '#22c55e',
  decision: '#f59e0b',
};

export default function CustomNode({ data, selected, type }) {
  const color = COLORS[type] || '#64748b';
  const status = data._status || ''; // running | done | error
  const cls = ['rf-node', selected && 'selected', status].filter(Boolean).join(' ');

  return (
    <div className={cls} style={{ borderLeft: `4px solid ${color}` }}>
      <Handle type="target" position={Position.Top} />
      <div className="type" style={{ color }}>{type}</div>
      <div className="name">{data.name || '(unnamed)'}</div>
      {type === 'llm' && data.model && <div className="meta">{data.model}</div>}
      {data._cost != null && <div className="meta">${data._cost.toFixed(4)} · {data._duration_ms?.toFixed(0)}ms</div>}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
