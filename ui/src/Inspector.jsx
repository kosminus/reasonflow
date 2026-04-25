import { useEffect, useState } from 'react';
import { postJSON } from './api';

export default function Inspector({ node, nodeTypes, providers, onChange, onDelete, refreshProviders }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  if (!node) {
    return (
      <aside className="inspector">
        <h3>Inspector</h3>
        <div className="empty">Select a node to edit. Drag from the palette to add nodes.</div>
      </aside>
    );
  }

  const def = nodeTypes.find(t => t.type === node.type);
  if (!def) return null;

  const setField = (key, value) => {
    onChange({ ...node, data: { ...node.data, [key]: value } });
  };

  const testModel = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await postJSON('/api/providers/test', { model: node.data.model });
      setTestResult(r);
    } catch (e) {
      setTestResult({ ok: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <aside className="inspector">
      <h3>{def.label} Node</h3>
      {def.fields.map((f) => {
        const val = node.data[f.key] ?? '';
        if (f.kind === 'model') {
          return <ModelPicker key={f.key} value={val} providers={providers}
                              onChange={v => setField(f.key, v)} onRefresh={refreshProviders}
                              onTest={testModel} testing={testing} testResult={testResult} />;
        }
        if (f.kind === 'textarea' || f.kind === 'code') {
          return (
            <div key={f.key}>
              <label>{f.label}</label>
              <textarea className={f.kind === 'code' ? 'code' : ''} value={val}
                        placeholder={f.placeholder}
                        onChange={e => setField(f.key, e.target.value)} />
            </div>
          );
        }
        if (f.kind === 'number') {
          return (
            <div key={f.key}>
              <label>{f.label}</label>
              <input type="number" step="0.1" value={val}
                     onChange={e => setField(f.key, parseFloat(e.target.value))} />
            </div>
          );
        }
        return (
          <div key={f.key}>
            <label>{f.label}{f.required && ' *'}</label>
            <input value={val} onChange={e => setField(f.key, e.target.value)} />
          </div>
        );
      })}

      <button className="delete" onClick={() => onDelete(node.id)}>Delete node</button>
    </aside>
  );
}

function ModelPicker({ value, providers, onChange, onRefresh, onTest, testing, testResult }) {
  const [providerId, setProviderId] = useState(() => guessProvider(value, providers));

  useEffect(() => {
    setProviderId(guessProvider(value, providers));
  }, [value, providers]);

  const provider = providers.find(p => p.id === providerId);
  const models = provider?.models || [];

  return (
    <div>
      <label>Provider</label>
      <select value={providerId} onChange={e => {
        const id = e.target.value;
        setProviderId(id);
        const p = providers.find(x => x.id === id);
        if (p?.models?.length) onChange(p.models[0]);
      }}>
        {providers.map(p => (
          <option key={p.id} value={p.id} disabled={!p.key_present}>
            {p.label}{p.key_present ? '' : ` — set ${p.env}`}
          </option>
        ))}
      </select>

      <label>Model
        {provider?.id === 'ollama' && (
          <button className="test-btn" style={{ float: 'right', marginTop: -2 }}
                  onClick={onRefresh}>↻</button>
        )}
      </label>
      {models.length > 0 ? (
        <select value={value} onChange={e => onChange(e.target.value)}>
          {!models.includes(value) && value && <option value={value}>{value} (custom)</option>}
          {models.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      ) : (
        <input value={value} placeholder={provider?.id === 'ollama' ? 'No local models. Run: ollama pull llama3' : 'model name'}
               onChange={e => onChange(e.target.value)} />
      )}

      <button className="test-btn" style={{ marginTop: 8 }} disabled={testing || !value} onClick={onTest}>
        {testing ? 'Testing...' : 'Test connection'}
      </button>
      {testResult && (
        <span className={`badge ${testResult.ok ? 'ok' : 'warn'}`}>
          {testResult.ok ? 'OK' : 'Failed'}
        </span>
      )}
      {testResult && !testResult.ok && (
        <div style={{ fontSize: 11, color: '#fca5a5', marginTop: 4 }}>{testResult.error}</div>
      )}
    </div>
  );
}

function guessProvider(model, providers) {
  if (!model) return providers[0]?.id;
  for (const p of providers) {
    if (p.models?.includes(model)) return p.id;
    if (p.prefix && model.startsWith(p.prefix)) return p.id;
  }
  if (model.startsWith('claude')) return 'anthropic';
  if (model.startsWith('gpt') || model.startsWith('o1')) return 'openai';
  return providers[0]?.id;
}
