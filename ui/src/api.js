const base = '';

export async function getJSON(path) {
  const r = await fetch(base + path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function postJSON(path, body) {
  const r = await fetch(base + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function delJSON(path) {
  const r = await fetch(base + path, { method: 'DELETE' });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function streamRun(runId, onEvent) {
  const es = new EventSource(`${base}/api/run/${runId}/stream`);
  es.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)); } catch {}
  };
  es.onerror = () => es.close();
  return es;
}
