"""GUI 对话 Tab 的 HTML / CSS / JS 片段。"""

CHAT_EXTRA_STYLES = """
  .chat-layout { display: flex; gap: 12px; height: calc(100vh - 220px); min-height: 420px; }
  .chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .chat-sidebar { width: 300px; flex-shrink: 0; display: flex; flex-direction: column; gap: 10px;
    overflow-y: auto; max-height: calc(100vh - 220px); }
  .chat-messages { flex: 1; overflow-y: auto; padding: 12px; border: 1px solid var(--border);
    border-radius: 10px; background: rgba(0,0,0,0.02); }
  .chat-msg { margin: 10px 0; max-width: 92%; }
  .chat-msg.user { margin-left: auto; text-align: right; }
  .chat-msg .bubble { display: inline-block; padding: 10px 14px; border-radius: 12px; font-size: 14px;
    line-height: 1.5; white-space: pre-wrap; text-align: left; }
  .chat-msg.user .bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 4px; }
  .chat-msg.assistant .bubble { background: var(--card); border: 1px solid var(--border);
    border-bottom-left-radius: 4px; }
  .chat-input-row { display: flex; gap: 8px; margin-top: 10px; }
  .chat-input-row textarea { flex: 1; resize: vertical; min-height: 44px; max-height: 120px;
    padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px;
    font-family: inherit; background: var(--card); color: var(--text); }
  .chat-input-row button { align-self: flex-end; padding: 10px 18px; }
  .chat-input-row button:disabled { opacity: 0.5; cursor: not-allowed; }
  .side-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px; font-size: 13px; }
  .side-card h4 { margin: 0 0 8px; font-size: 13px; font-weight: 600; }
  .side-card ul { margin: 0; padding-left: 18px; }
  .side-card li { margin: 4px 0; color: var(--muted); }
  .llm-badge { font-size: 11px; color: var(--muted); }
  .llm-badge.warn { color: var(--warn); }
  .progress-bar { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden;
    margin: 8px 0 10px; }
  .progress-bar span { display: block; height: 100%; background: var(--accent); border-radius: 3px;
    transition: width 0.3s ease; }
  .check-list { list-style: none; padding: 0; margin: 0; }
  .check-list li { padding: 3px 0; font-size: 12px; color: var(--muted); }
  .check-list li.done { color: var(--ok); }
  .check-list li.done::before { content: '✓ '; }
  .check-list li:not(.done)::before { content: '○ '; color: var(--border); }
  .preview-name { font-weight: 600; font-size: 14px; margin: 0 0 4px; }
  .preview-role { color: var(--muted); font-size: 12px; margin: 0 0 8px; }
  .preview-tags { display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0; }
  .preview-tag { font-size: 11px; background: rgba(0,113,227,0.1); color: var(--accent);
    padding: 2px 7px; border-radius: 4px; }
  .hint-chips { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
  .hint-chip { text-align: left; background: rgba(0,113,227,0.08); border: 1px solid rgba(0,113,227,0.2);
    color: var(--text); border-radius: 8px; padding: 8px 10px; font-size: 12px; cursor: pointer;
    line-height: 1.4; }
  .hint-chip:hover { background: rgba(0,113,227,0.14); }
  nav button.locked { opacity: 0.45; cursor: not-allowed; }
  @media (max-width: 900px) {
    .chat-layout { flex-direction: column; height: auto; }
    .chat-sidebar { width: 100%; max-height: none; }
  }
"""

CHAT_PANEL_HTML = """
  <section id="panel-chat" class="panel active">
  <div class="chat-layout">
    <div class="chat-main">
      <div class="chat-messages" id="chatMessages"></div>
      <div class="chat-input-row">
        <textarea id="chatInput" placeholder="随便聊聊你的背景、困惑或目标…" rows="2"></textarea>
        <button id="chatSendBtn" onclick="chatSend()">发送</button>
      </div>
    </div>
    <aside class="chat-sidebar">
      <div class="side-card">
        <h4>实时画像</h4>
        <div id="profilePreview"><p class="muted">对话中自动更新…</p></div>
      </div>
      <div class="side-card">
        <h4>完成度 <span id="progressPct" class="muted">0%</span></h4>
        <div class="progress-bar"><span id="progressFill" style="width:0%"></span></div>
        <ul class="check-list" id="progressChecks"></ul>
      </div>
      <div class="side-card">
        <h4>认识自己</h4>
        <p id="intakeStatus">加载中…</p>
        <ul id="intakeGaps"></ul>
      </div>
      <div class="side-card" id="hintCard">
        <h4>建议追问</h4>
        <div class="hint-chips" id="gapHints"></div>
      </div>
      <div class="side-card">
        <h4>LLM</h4>
        <p class="llm-badge" id="llmStatus">检测中…</p>
      </div>
    </aside>
  </div>
</section>
"""

CHAT_EXTRA_SCRIPT = """
function renderJourney(journey) {
  if (!journey || !journey.steps) return;
  const bar = document.getElementById('journeyBar');
  const hint = document.getElementById('journeyHint');
  const sub = document.getElementById('journeySubtitle');
  if (!bar || !hint) return;
  const coreDone = !!journey.core_complete;
  bar.classList.toggle('complete', coreDone);
  hint.classList.toggle('complete', coreDone);
  bar.innerHTML = journey.steps.map((s, i) => {
    const cls = ['journey-step'];
    if (s.optional) cls.push('optional');
    if (s.done) cls.push('done');
    if (s.current) cls.push('current');
    return `<div class="${cls.join(' ')}"><span class="num">${i + 1}</span><span class="label">${escapeHtml(s.title)}</span></div>`;
  }).join('') + (coreDone ? '<div class="journey-complete-badge">✓ 已完成</div>' : '');
  if (coreDone) {
    hint.textContent = journey.next_hint || '核心流程已完成';
    if (sub) sub.textContent = '已完成 — 机会矩阵已就绪';
  } else {
    hint.textContent = '下一步：' + (journey.next_hint || '');
    if (sub && journey.current_title) {
      sub.textContent = '当前：' + journey.current_title;
    }
  }
}

function renderProfilePreview(preview) {
  const el = document.getElementById('profilePreview');
  if (!preview || (!preview.name && !preview.current_role && !preview.education.length)) {
    el.innerHTML = '<p class="muted">尚无结构化信息，继续聊即可。</p>';
    return;
  }
  let html = '';
  if (preview.name) html += `<p class="preview-name">${escapeHtml(preview.name)}</p>`;
  if (preview.current_role) html += `<p class="preview-role">${escapeHtml(preview.current_role)}</p>`;
  if (preview.education.length) {
    html += '<p class="muted" style="margin:4px 0">教育</p><ul>';
    preview.education.forEach(e => { html += `<li>${escapeHtml(e)}</li>`; });
    html += '</ul>';
  }
  if (preview.core_skills.length) {
    html += '<div class="preview-tags">';
    preview.core_skills.forEach(s => { html += `<span class="preview-tag">${escapeHtml(s)}</span>`; });
    html += '</div>';
  }
  if (preview.values.length) {
    html += '<p class="muted" style="margin:6px 0 4px">价值排序</p><div class="preview-tags">';
    preview.values.forEach(v => { html += `<span class="preview-tag">${escapeHtml(v)}</span>`; });
    html += '</div>';
  }
  if (preview.evidence_count) {
    html += `<p class="muted" style="margin:4px 0">${preview.evidence_count} 条优势证据</p>`;
  }
  el.innerHTML = html;
}

function renderProgress(progress) {
  const pct = (progress && progress.percent) || 0;
  document.getElementById('progressPct').textContent = pct + '%';
  document.getElementById('progressFill').style.width = pct + '%';
  const checksEl = document.getElementById('progressChecks');
  const checks = (progress && progress.checks) || [];
  checksEl.innerHTML = checks.map(c =>
    `<li class="${c.done ? 'done' : ''}">${escapeHtml(c.label)}</li>`
  ).join('');
}

function renderGapHints(hints) {
  const card = document.getElementById('hintCard');
  const el = document.getElementById('gapHints');
  if (!hints || !hints.length) {
    card.style.display = 'none';
    return;
  }
  card.style.display = 'block';
  el.innerHTML = hints.map(h =>
    `<button type="button" class="hint-chip" onclick="useHint(this)">${escapeHtml(h)}</button>`
  ).join('');
}

function useHint(btn) {
  const input = document.getElementById('chatInput');
  input.value = btn.textContent;
  input.focus();
}

function updateTabLocks(intakeComplete) {
  ['trends', 'jobs', 'matrix'].forEach(name => {
    const btn = document.getElementById('tab-' + name);
    if (intakeComplete) {
      btn.classList.remove('locked');
      btn.removeAttribute('title');
    } else {
      btn.classList.add('locked');
      btn.title = '请先完成「认识自己」，再查看此 Tab';
    }
  });
}

function showTabSafe(name) {
  if (['trends', 'jobs', 'matrix'].includes(name)) {
    const btn = document.getElementById('tab-' + name);
    if (btn.classList.contains('locked')) {
      toast('请先完成「认识自己」，再继续探索');
      showTab('chat');
      return;
    }
  }
  showTab(name);
}

function renderChatMessages(messages) {
  const box = document.getElementById('chatMessages');
  box.innerHTML = messages.map(m =>
    `<div class="chat-msg ${m.role}"><div class="bubble">${escapeHtml(m.content)}</div></div>`
  ).join('');
  box.scrollTop = box.scrollHeight;
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text || '';
  return d.innerHTML;
}

function renderChatState(state) {
  renderChatMessages(state.messages || []);
  const llm = state.llm || {};
  const llmEl = document.getElementById('llmStatus');
  if (!llm.configured) {
    llmEl.textContent = '未配置 LLM（CloudBase / Anthropic / OpenAI）';
    llmEl.className = 'llm-badge warn';
  } else {
    llmEl.textContent = llm.provider + ' · ' + llm.model;
    llmEl.className = 'llm-badge';
  }
  const statusEl = document.getElementById('intakeStatus');
  const gapsEl = document.getElementById('intakeGaps');
  const errors = (state.validation && state.validation.errors) || [];
  if (state.intake_complete) {
    statusEl.textContent = '✅ 「认识自己」已完成，可进入「探索世界」';
    gapsEl.innerHTML = '';
  } else if (errors.length) {
    statusEl.textContent = '认识自己 · 待补齐 ' + errors.length + ' 项';
    gapsEl.innerHTML = errors.slice(0, 5).map(e => '<li>' + escapeHtml(e) + '</li>').join('');
  } else {
    statusEl.textContent = '继续对话，完善对自己的认识';
    gapsEl.innerHTML = '';
  }
  renderProfilePreview(state.profile_preview);
  renderProgress(state.progress);
  renderGapHints(state.gap_hints);
  updateTabLocks(!!state.intake_complete);
  if (state.journey) renderJourney(state.journey);
}

async function loadChatState() {
  const state = await pywebview.api.chat_state();
  renderChatState(state);
  return state;
}

async function chatSend() {
  const input = document.getElementById('chatInput');
  const btn = document.getElementById('chatSendBtn');
  const text = input.value.trim();
  if (!text) return;
  btn.disabled = true;
  input.value = '';
  const box = document.getElementById('chatMessages');
  box.innerHTML += `<div class="chat-msg user"><div class="bubble">${escapeHtml(text)}</div></div>`;
  box.innerHTML += `<div class="chat-msg assistant" id="chatPending"><div class="bubble">思考中…</div></div>`;
  box.scrollTop = box.scrollHeight;
  try {
    const res = await pywebview.api.chat_send(text);
    document.getElementById('chatPending')?.remove();
    if (res.messages) renderChatMessages(res.messages);
    renderChatState(res);
    if (res.files_updated && res.files_updated.length) {
      toast('已更新: ' + res.files_updated.join(', '));
    }
    await refresh();
    if (res.just_completed) {
      toast('🎉 「认识自己」已完成！');
      setTimeout(() => showTab('profile'), 800);
    }
  } catch (e) {
    document.getElementById('chatPending')?.remove();
    toast('发送失败: ' + e);
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

document.addEventListener('keydown', (e) => {
  if (currentTab !== 'chat') return;
  if (e.key === 'Enter' && !e.shiftKey && document.activeElement === document.getElementById('chatInput')) {
    e.preventDefault();
    chatSend();
  }
});
"""
