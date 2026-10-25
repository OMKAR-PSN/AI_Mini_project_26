/** Shared SSE transport. A clean EOF without a terminal event is an error. */
export async function streamEvents(url: string, payload: unknown, onEvent: (event: Record<string, unknown>) => void, signal?: AbortSignal) {
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal });
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(typeof body?.detail === 'string' ? body.detail : `Analysis request failed (${response.status})`); }
  if (!response.body) throw new Error('The server returned no analysis stream.');
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '', data: string[] = [], completed = false;
  const dispatch = () => { if (!data.length) return; const event = JSON.parse(data.join('\n')); data = []; if (!event || typeof event.type !== 'string') throw new Error('Invalid analysis event.'); if (signal?.aborted) return; onEvent(event); if (event.type === 'completed') completed = true; };
  const line = (value: string) => { if (value === '') dispatch(); else if (value.startsWith('data:')) data.push(value.slice(5).trimStart()); };
  try {
    while (!completed) { const { done, value } = await reader.read(); if (done) { buffer += decoder.decode(); if (buffer) line(buffer.replace(/\r$/, '')); dispatch(); break; } buffer += decoder.decode(value, { stream: true }); let end; while ((end = buffer.indexOf('\n')) >= 0) { line(buffer.slice(0, end).replace(/\r$/, '')); buffer = buffer.slice(end + 1); if (completed) break; } }
    if (!completed && !signal?.aborted) throw new Error('Analysis connection ended before a result arrived. Run again to obtain a complete record.');
  } finally { await reader.cancel().catch(() => { }); reader.releaseLock(); }
}
