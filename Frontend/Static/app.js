const state = {
  sessionId: localStorage.getItem('tvcapital_session_id') || makeSessionId(),
  sessions: readSessions(),
  responseSeq: 0,
  lastResponse: null,
  busy: false,
};

const els = {
  chatScroll: document.getElementById('chatScroll'),
  messages: document.getElementById('messages'),
  welcome: document.getElementById('welcomeView'),
  query: document.getElementById('queryInput'),
  send: document.getElementById('sendBtn'),
  typing: document.getElementById('typingRow'),
  sessionList: document.getElementById('sessionList'),
  inspector: document.getElementById('inspector'),
  inspectorContent: document.getElementById('inspectorContent'),
  inspectorEmpty: document.getElementById('inspectorEmpty'),
  healthDot: document.getElementById('healthDot'),
  healthText: document.getElementById('healthText'),
  healthMeta: document.getElementById('healthMeta'),
  toastStack: document.getElementById('toastStack'),
};

const UNCLASSIFIED = 'All companies (unclassified)';

/* ───────────────────────── helpers ───────────────────────── */
function icon(name, cls = 'h-4 w-4') {
  const d = (window.ICONS || {})[name] || '';
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
}

function makeSessionId() {
  const seed = Math.random().toString(36).slice(2, 9);
  return `tvc-${Date.now().toString(36)}-${seed}`;
}

function readSessions() {
  try { return JSON.parse(localStorage.getItem('tvcapital_sessions') || '[]'); }
  catch { return []; }
}

function saveSessions() {
  localStorage.setItem('tvcapital_sessions', JSON.stringify(state.sessions.slice(0, 12)));
  localStorage.setItem('tvcapital_session_id', state.sessionId);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}
function escapeAttr(value) { return escapeHtml(value).replaceAll('`', '&#096;'); }

function formatTime(ts) {
  if (!ts) return '';
  return new Date(ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
function formatDuration(sec) { return typeof sec === 'number' ? `${sec.toFixed(1)}s` : ''; }
function formatKey(key) { return String(key).replaceAll('_', ' ').replace(/^\w/, c => c.toUpperCase()); }
function formatValue(value) {
  if (Array.isArray(value)) return value.join(', ');
  if (value && typeof value === 'object') return JSON.stringify(value);
  return String(value ?? '');
}
function companyLabel(payload) {
  const fc = payload.filters_used?.company;
  if (fc && fc !== UNCLASSIFIED) return fc;
  if (payload.route === 'unclassified') return 'All companies';
  return payload.company || 'Portfolio';
}

/* ───────────────────────── sessions ───────────────────────── */
function upsertSession(title, company = '') {
  const existing = state.sessions.find(s => s.id === state.sessionId);
  if (existing) {
    if (title && existing.title === 'New conversation') existing.title = title;
    if (company) existing.company = company;
    existing.updatedAt = Date.now();
  } else {
    state.sessions.unshift({ id: state.sessionId, title: title || 'New conversation', company, updatedAt: Date.now() });
  }
  state.sessions.sort((a, b) => b.updatedAt - a.updatedAt);
  saveSessions();
  renderSessions();
}

function renderSessions() {
  if (!state.sessions.length) {
    els.sessionList.innerHTML = '<div class="px-2 py-3 text-xs leading-relaxed text-[#9fb3c6]">Your conversations will appear here.</div>';
    return;
  }
  els.sessionList.innerHTML = state.sessions.map(s => {
    const active = s.id === state.sessionId;
    return `
      <button data-session-id="${escapeAttr(s.id)}"
        class="mb-1 flex w-full items-center gap-2.5 rounded-lg px-2 py-2.5 text-left transition ${active ? 'bg-white/10 text-white' : 'text-[#aeb9c8] hover:bg-white/5 hover:text-white'}">
        <span class="grid h-7 w-7 shrink-0 place-items-center rounded-lg ${active ? 'bg-brand-cyan/15 text-brand-cyan' : 'bg-white/5 text-[#7c8da4]'}">${icon('file', 'h-3.5 w-3.5')}</span>
        <span class="min-w-0">
          <span class="block truncate text-[13px] font-medium">${escapeHtml(s.title || 'New conversation')}</span>
          <span class="mt-0.5 block text-[11px] text-[#9fb3c6]">${escapeHtml(s.company || 'Portfolio')}, ${formatTime(s.updatedAt)}</span>
        </span>
      </button>`;
  }).join('');

  els.sessionList.querySelectorAll('[data-session-id]').forEach(btn => {
    btn.addEventListener('click', () => { loadSession(btn.dataset.sessionId); closeSidebarMobile(); });
  });
}

/* ───────────────────────── markdown ───────────────────────── */
function inlineMd(s) {
  return s
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)/g, '<em>$1</em>')
    .replace(/\[([0-9]+)\]/g, (_, n) => `<a class="citation-link" href="#" data-source-ref="${n}">[${n}]</a>`);
}

function renderMarkdown(text) {
  if (!text) return '';
  const lines = escapeHtml(text).split('\n');
  const out = [];
  let para = [], list = null, table = null, code = null;

  const flushPara = () => { if (para.length) { out.push(`<p>${inlineMd(para.join('<br>'))}</p>`); para = []; } };
  const flushList = () => { if (list) { out.push(`<${list.type}>${list.items.map(i => `<li>${inlineMd(i)}</li>`).join('')}</${list.type}>`); list = null; } };
  const flushTable = () => {
    if (!table) return;
    const [head, ...body] = table;
    out.push(`<table><thead><tr>${head.map(c => `<th>${inlineMd(c)}</th>`).join('')}</tr></thead><tbody>${
      body.map(r => `<tr>${r.map(c => `<td>${inlineMd(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
    table = null;
  };
  const flushAll = () => { flushPara(); flushList(); flushTable(); };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (code !== null) {
      if (line.trim().startsWith('```')) { out.push(`<pre><code>${code.join('\n')}</code></pre>`); code = null; }
      else code.push(raw);
      continue;
    }
    if (line.trim().startsWith('```')) { flushAll(); code = []; continue; }

    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { flushAll(); out.push(h[1].length <= 3 ? `<h3>${inlineMd(h[2])}</h3>` : `<h4>${inlineMd(h[2])}</h4>`); continue; }

    if (/^\s*\|.*\|\s*$/.test(line)) {
      flushPara(); flushList();
      const cells = line.trim().slice(1, -1).split('|').map(c => c.trim());
      if (cells.every(c => /^:?-{2,}:?$/.test(c))) continue; // separator row
      (table ||= []).push(cells);
      continue;
    } else flushTable();

    const ul = line.match(/^\s*[-*•]\s+(.*)$/);
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (ul || ol) {
      flushPara();
      const type = ul ? 'ul' : 'ol';
      if (list && list.type !== type) flushList();
      (list ||= { type, items: [] }).items.push((ul || ol)[1]);
      continue;
    }

    if (!line.trim()) { flushAll(); continue; }
    flushList();
    para.push(line);
  }
  if (code !== null) out.push(`<pre><code>${code.join('\n')}</code></pre>`);
  flushAll();
  return out.join('');
}

/* ───────────────────────── messages ───────────────────────── */
const chip = (text, accent = false) =>
  `<span class="rounded border px-2 py-1 text-[11px] uppercase font-medium ${accent
    ? 'border-brand-teal/30 bg-brand-sky text-brand-tealdeep'
    : 'border-brand-line bg-brand-grey text-brand-muted'}">${escapeHtml(text)}</span>`;

function addUserMessage(text) {
  els.welcome.classList.add('hidden');
  els.messages.insertAdjacentHTML('beforeend', `
    <div class="my-3 flex justify-end gap-2.5">
      <div class="max-w-[80%] rounded-lg rounded-br-none bg-brand-navy px-4 py-3 text-[15px] leading-relaxed text-white max-sm:max-w-[88%]">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
      <div class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-sky text-xs font-bold text-brand-navy2">You</div>
    </div>`);
  scrollToBottom();
}

function addAssistantMessage(payload) {
  els.welcome.classList.add('hidden');
  const responseId = `response-${++state.responseSeq}`;
  const sources = Array.isArray(payload.citations) ? payload.citations.length : 0;
  const duration = formatDuration(payload.latency_seconds);

  els.messages.insertAdjacentHTML('beforeend', `
    <div class="my-3 flex gap-2.5" data-response-id="${responseId}">
      <div class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-navy text-brand-cyan">${icon('spark')}</div>
      <div class="min-w-0 flex-1 max-w-[88%]">
        <div class="answer-prose rounded-lg rounded-bl-none border border-brand-line bg-white px-4 py-3 text-[15px] leading-relaxed text-brand-ink">${renderMarkdown(payload.answer || '')}</div>
        <div class="mt-2.5 flex flex-wrap items-center gap-1.5">
          ${chip(companyLabel(payload), true)}
          ${duration ? chip(duration) : ''}
          ${sources ? chip(`${sources} source file${sources === 1 ? '' : 's'}`) : ''}
        </div>
        <div class="mt-2 flex gap-1">
          <button data-copy-answer class="inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-brand-muted hover:bg-brand-grey hover:text-brand-muted">${icon('copy', 'h-3.5 w-3.5')} Copy</button>
          ${sources ? `<button data-open-sources class="inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-brand-muted hover:bg-brand-grey hover:text-brand-muted">${icon('panel', 'h-3.5 w-3.5')} Sources</button>` : ''}
        </div>
      </div>
    </div>`);

  const row = els.messages.lastElementChild;
  row.querySelector('[data-copy-answer]')?.addEventListener('click', () => copyText(payload.answer || ''));
  row.querySelector('[data-open-sources]')?.addEventListener('click', () => openInspector(payload));
  row.querySelectorAll('[data-source-ref]').forEach(link => link.addEventListener('click', e => {
    e.preventDefault();
    openInspector(payload, link.dataset.sourceRef);
  }));
  scrollToBottom();
}

function addErrorMessage(message) {
  els.messages.insertAdjacentHTML('beforeend', `
    <div class="my-3 flex gap-2.5">
      <div class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#7a2e38] text-white">${icon('close')}</div>
      <div class="max-w-[min(78%,730px)] rounded-lg rounded-bl-none border border-[#f0d5d9] bg-[#fdf5f6] px-4 py-3 text-[14px] leading-relaxed text-[#6b2c36]">
        <strong>The request failed.</strong><br>${escapeHtml(message)}
      </div>
    </div>`);
  scrollToBottom();
}

/* ───────────────────────── inspector ───────────────────────── */
const block = (title, body) => `
  <div class="mb-3 rounded-xl border border-brand-line bg-white p-3.5">
    <div class="mb-2.5 text-[12px] font-semibold uppercase text-brand-navy2">${title}</div>
    ${body}
  </div>`;
const note = text => `<div class="rounded-lg border border-brand-line bg-brand-grey px-2.5 py-2 text-xs text-brand-muted">${text}</div>`;
const metaRows = obj => Object.entries(obj || {})
  .filter(([k]) => !['file_name', 'current_path'].includes(k))
  .map(([k, v]) => `
    <div class="flex justify-between gap-3 text-xs">
      <span class="shrink-0 text-brand-muted">${escapeHtml(formatKey(k))}</span>
      <span class="text-right font-medium text-brand-ink [overflow-wrap:anywhere]">${escapeHtml(formatValue(v))}</span>
    </div>`).join('');

function renderInspector(payload, focusRef = null) {
  state.lastResponse = payload;
  els.inspectorEmpty.classList.add('hidden');
  els.inspectorContent.classList.remove('hidden');

  const filters = payload.filters_used || {};
  const sources = Array.isArray(payload.citations) ? payload.citations : [];
  const selected = Array.isArray(filters.llm_selected_filters) ? filters.llm_selected_filters : [];
  const trace = Array.isArray(filters.retrieval_trace) ? filters.retrieval_trace : [];
  const summary = metaRows(payload.metadata_summary);

  const sourceHtml = sources.length ? sources.map((s, i) => {
    const refs = Array.isArray(s.refs) ? s.refs : [];
    const name = s.file_name || 'Unnamed file';
    const path = s.current_path || '';
    const open = path ? `data-open-blob data-blob-path="${escapeAttr(path)}"` : '';
    const rows = metaRows(s.metadata);
    return `
      <div class="border-b border-brand-line py-3 first:pt-0 last:border-0 last:pb-0" data-source-ref-list="${escapeAttr(refs.join(','))}" id="inspector-source-${i}">
        ${path
          ? `<button type="button" ${open} title="Open ${escapeAttr(name)} in a new tab" class="group flex w-full items-start gap-2 text-left disabled:cursor-wait disabled:opacity-60">
               <span class="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md bg-brand-sky text-brand-tealdeep group-[.loading]:animate-spin">${icon('external', 'h-3 w-3')}</span>
               <span class="text-[13px] font-semibold leading-snug text-brand-ink group-hover:underline group-hover:underline-offset-2">${escapeHtml(name)}</span>
             </button>
             <button type="button" ${open} class="mt-1 block w-full text-left text-[11px] leading-snug text-brand-muted [overflow-wrap:anywhere] hover:text-brand-tealdeep hover:underline">${escapeHtml(path)}</button>`
          : `<div class="text-[13px] font-semibold text-brand-ink">${escapeHtml(name)}</div>`}
        <div class="mt-2 flex flex-wrap gap-1">
          ${refs.map(r => `<span class="rounded-md bg-brand-sky px-1.5 py-0.5 text-[11px] font-semibold text-brand-tealdeep">[${escapeHtml(r)}]</span>`).join('')}
        </div>
        ${rows ? `
          <details class="group/meta mt-2">
            <summary class="cursor-pointer select-none text-xs text-brand-muted hover:text-ink">File metadata</summary>
            <div class="mt-2 flex flex-col gap-1.5 rounded-lg bg-brand-grey p-2.5">${rows}</div>
          </details>` : ''}
      </div>`;
  }).join('') : note('No files were cited for this answer.');

  const filterHtml = selected.length
    ? selected.map(f => note(`<strong class="text-brand-ink">${escapeHtml(formatKey(f.field || ''))}</strong>: ${escapeHtml((f.values || []).join(', '))}`)).join('')
    : note(payload.route === 'unclassified' ? 'Company not identified, so the whole index was searched without filters.' : 'No metadata filters were applied.');

  const traceHtml = trace.length
    ? trace.map(t => note(`<strong class="text-brand-ink">${escapeHtml(t.stage || 'stage')}</strong>: ${Number(t.hits || 0)} hits, ${Number(t.new_chunks || 0)} new`)).join('')
    : note('No search steps were returned.');

  els.inspectorContent.innerHTML = `
    ${block('Answered from', `
      <div class="flex items-center justify-between gap-2">
        <div>
          <div class="text-sm font-semibold text-brand-ink">${escapeHtml(companyLabel(payload))}</div>
          <div class="mt-0.5 text-xs text-brand-muted">Route: ${escapeHtml(payload.route || 'unknown')}</div>
        </div>
        ${payload.latency_seconds != null ? chip(formatDuration(payload.latency_seconds), true) : ''}
      </div>`)}
    ${block(`Files cited (${sources.length})`, sourceHtml)}
    ${block('Metadata across cited files', summary ? `<div class="flex flex-col gap-1.5">${summary}</div>` : note('No metadata returned.'))}
    ${block('Filters applied', `<div class="flex flex-col gap-1.5">${filterHtml}</div>`)}
    ${block('Search steps', `<div class="flex flex-col gap-1.5">${traceHtml}</div>`)}
  `;

  showInspector();

  els.inspectorContent.querySelectorAll('[data-open-blob]').forEach(btn =>
    btn.addEventListener('click', () => openBlobDocument(btn.dataset.blobPath, btn)));

  if (focusRef != null) {
    const target = [...els.inspectorContent.querySelectorAll('[data-source-ref-list]')]
      .find(card => card.dataset.sourceRefList.split(',').includes(String(focusRef)));
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      target.classList.add('bg-brand-sky', 'rounded-lg');
      setTimeout(() => target.classList.remove('bg-brand-sky', 'rounded-lg'), 1400);
    }
  }
}

function openInspector(payload = null, focusRef = null) {
  if (payload) { renderInspector(payload, focusRef); return; }
  showInspector();
}
function showInspector() {
  els.inspector.classList.add('open');
  els.inspector.setAttribute('aria-hidden', 'false');
  document.getElementById('sourceToggleBtn')?.setAttribute('aria-expanded', 'true');
}
function closeInspector() {
  els.inspector.classList.remove('open');
  els.inspector.setAttribute('aria-hidden', 'true');
  document.getElementById('sourceToggleBtn')?.setAttribute('aria-expanded', 'false');
}

async function openBlobDocument(blobPath, button) {
  if (!blobPath) return;
  if (button) { button.disabled = true; button.classList.add('loading'); }
  const tab = window.open('about:blank', '_blank'); // open during the click so popup blockers allow it
  try {
    const res = await fetch('/documents/sas-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blob_path: blobPath }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.url) {
      tab?.close();
      throw new Error(data.detail || `Could not open the file (HTTP ${res.status}).`);
    }
    if (tab) tab.location.href = data.url; else window.location.href = data.url;
  } catch (err) {
    showToast(err.message || 'Could not open the file.', true);
  } finally {
    if (button) { button.disabled = false; button.classList.remove('loading'); }
  }
}

/* ───────────────────────── backend calls ───────────────────────── */
async function checkHealth() {
  try {
    const res = await fetch('/health', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    els.healthDot.className = 'h-2 w-2 shrink-0 rounded-full bg-brand-cyan shadow-[0_0_0_4px_rgba(5,223,254,.15)]';
    els.healthText.textContent = 'Connected';
    els.healthMeta.textContent = data.index || 'search index';
  } catch {
    els.healthDot.className = 'h-2 w-2 shrink-0 rounded-full bg-[#c85f6d]';
    els.healthText.textContent = 'Backend not reachable';
    els.healthMeta.textContent = 'Start the FastAPI server and refresh';
  }
}

async function loadSession(sessionId) {
  state.sessionId = sessionId;
  saveSessions();
  renderSessions();
  clearConversationView();
  try {
    const res = await fetch(`/history/${encodeURIComponent(sessionId)}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const turns = Array.isArray(data.turns) ? data.turns : [];
    turns.forEach(turn => {
      if (turn.user) addUserMessage(turn.user);
      if (turn.assistant) addAssistantMessage({
        answer: turn.assistant,
        company: turn.company,
        route: turn.question_type,
        latency_seconds: null,
        citations: [],
        filters_used: { company: turn.company || UNCLASSIFIED },
      });
    });
  } catch {
    showToast('Could not load this conversation.', true);
  }
}

function clearConversationView() {
  els.messages.innerHTML = '';
  els.welcome.classList.remove('hidden');
  els.inspectorContent.classList.add('hidden');
  els.inspectorEmpty.classList.remove('hidden');
  state.lastResponse = null;
}

function newConversation() {
  state.sessionId = makeSessionId();
  upsertSession('New conversation');
  clearConversationView();
  els.query.value = '';
  updateSendState();
  closeInspector();
  closeSidebarMobile();
  els.query.focus();
}

async function sendMessage() {
  const query = els.query.value.trim();
  if (!query || state.busy) return;

  state.busy = true;
  updateSendState();
  els.query.value = '';
  resizeTextarea();
  addUserMessage(query);
  upsertSession(query.slice(0, 58) + (query.length > 58 ? '…' : ''));
  setTyping(true);

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId, query }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || `Request failed with HTTP ${res.status}`);
    addAssistantMessage(data);
    upsertSession('', companyLabel(data));
    if (Array.isArray(data.citations) && data.citations.length) renderInspector(data);
  } catch (err) {
    addErrorMessage(err.message || 'The request failed.');
  } finally {
    setTyping(false);
    state.busy = false;
    updateSendState();
  }
}

/* ───────────────────────── UI utils ───────────────────────── */
function setTyping(on) {
  els.typing.classList.toggle('hidden', !on);
  els.typing.classList.toggle('flex', on);
  if (on) scrollToBottom();
}
function scrollToBottom() {
  requestAnimationFrame(() => els.chatScroll.scrollTo({ top: els.chatScroll.scrollHeight, behavior: 'smooth' }));
}
function updateSendState() { els.send.disabled = state.busy || !els.query.value.trim(); }
function resizeTextarea() { els.query.style.height = 'auto'; els.query.style.height = `${Math.min(els.query.scrollHeight, 170)}px`; }
function openSidebarMobile() { document.getElementById('sidebar').classList.add('open'); }
function closeSidebarMobile() { document.getElementById('sidebar').classList.remove('open'); }

function showToast(message, error = false) {
  const el = document.createElement('div');
  el.className = `max-w-[340px] animate-toast-in rounded-xl px-3.5 py-3 text-[13px] text-white shadow-2xl ${error ? 'bg-[#7a2e38]' : 'bg-brand-navy'}`;
  el.textContent = message;
  els.toastStack.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); showToast('Answer copied.'); }
  catch { showToast('Copy is not available in this browser.', true); }
}

function clearLocalSessions() {
  state.sessions = [];
  saveSessions();
  renderSessions();
  showToast('Recent conversations cleared from this browser.');
}

function bindEvents() {
  document.getElementById('newChatBtn').addEventListener('click', newConversation);
  document.getElementById('sourceToggleBtn').addEventListener('click', () => {
    if (els.inspector.classList.contains('open')) closeInspector();
    else if (state.lastResponse) openInspector(state.lastResponse);
    else showInspector();
  });
  document.getElementById('inspectorCloseBtn').addEventListener('click', closeInspector);
  document.getElementById('mobileMenuBtn').addEventListener('click', openSidebarMobile);
  document.getElementById('clearLocalBtn').addEventListener('click', clearLocalSessions);

  els.query.addEventListener('input', () => { resizeTextarea(); updateSendState(); });
  els.query.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  els.send.addEventListener('click', sendMessage);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeInspector(); closeSidebarMobile(); } });

  document.querySelectorAll('[data-prompt]').forEach(btn => btn.addEventListener('click', () => {
    els.query.value = btn.dataset.prompt;
    resizeTextarea(); updateSendState(); els.query.focus();
  }));
}

window.addEventListener('DOMContentLoaded', () => {
  bindEvents();
  renderSessions();
  checkHealth();
  if (!state.sessions.some(s => s.id === state.sessionId)) upsertSession('New conversation');
  else loadSession(state.sessionId);
  setInterval(checkHealth, 30000);
});