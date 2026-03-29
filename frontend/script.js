/**
 * VoxLens — Frontend Script
 * Fixes: Groq API, live news chatbot, real regional news, dark mode
 */

// ── CONFIG ──
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000/api'
  : 'https://voxlens-backend-zqr7.onrender.com/api';

// ── STATE ──
let currentArticle  = null;
let chatHistory     = [];
let isSpeaking      = false;
let currentUtterance = null;
let loadedFeatures  = {};
let discussionArticles = [];
let allLoadedArticles = [];
let userCity        = null;

// ═══════════════════════════════════════
// INIT
// ═══════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  // Restore theme
  const saved = localStorage.getItem('voxlens-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);

  // Load news
  loadHeadlines('general', document.querySelector('.filter-btn.active'));

  // Background loads
  setTimeout(() => {
    loadBriefArticles();
    loadTimelineArticles();
    fetchGuidelines();
  }, 600);

  // Auto-detect location silently
  detectLocationSilent();

  // Chat input auto-resize
  const ci = document.getElementById('chatInput');
  if (ci) ci.addEventListener('input', () => {
    ci.style.height = 'auto';
    ci.style.height = Math.min(ci.scrollHeight, 120) + 'px';
  });

  // Char counter
  const ct = document.getElementById('commentText');
  if (ct) ct.addEventListener('input', updateCharCount);
});

// ═══════════════════════════════════════
// THEME TOGGLE
// ═══════════════════════════════════════

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  localStorage.setItem('voxlens-theme', next);
  showToast(next === 'dark' ? '🌙 Dark mode on' : '☀️ Light mode on');
}

// ═══════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════

function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

  const hero = document.getElementById('heroSection');
  if (hero) hero.style.display = name === 'home' ? '' : 'none';

  const sec = document.getElementById(`section-${name}`);
  if (sec) sec.classList.add('active');

  const nl = document.querySelector(`[data-section="${name}"]`);
  if (nl) nl.classList.add('active');

  if (name === 'local') initLocalNews();

  document.getElementById('navLinks').classList.remove('open');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function toggleMenu() {
  document.getElementById('navLinks').classList.toggle('open');
}

// ═══════════════════════════════════════
// NEWS LOADING
// ═══════════════════════════════════════

async function loadHeadlines(category, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const container = document.getElementById('homeArticles');
  container.innerHTML = skeletonHtml(6);

  try {
    // Use India as default (can be overridden later by detected country)
    const res = await fetch(`${API_BASE}/news/headlines?country=in&category=${category}&page_size=20`);
    const data = await res.json();
    allLoadedArticles = data.articles || [];
    renderGrid(container, allLoadedArticles);
    updateDiscussionSelect(allLoadedArticles);
    discussionArticles = allLoadedArticles;
  } catch (err) {
    container.innerHTML = `<div class="loading-msg">⚠️ Could not load news. Check API keys &amp; connection.<br><small style="color:var(--text4)">${err.message}</small></div>`;
  }
}

async function loadBriefArticles() {
  const c = document.getElementById('briefArticles');
  try {
    const res = await fetch(`${API_BASE}/news/headlines?country=in&page_size=10`);
    const data = await res.json();
    renderBriefList(c, data.articles || []);
  } catch {
    c.innerHTML = '<div class="loading-msg">Could not load articles.</div>';
  }
}

async function loadTimelineArticles() {
  const c = document.getElementById('timelineArticles');
  try {
    const res = await fetch(`${API_BASE}/news/headlines?country=in&page_size=8`);
    const data = await res.json();
    renderTimelineList(c, data.articles || []);
  } catch {
    c.innerHTML = '<div class="loading-msg">Could not load articles.</div>';
  }
}

// ── RENDER HELPERS ──

function renderGrid(container, articles) {
  if (!articles || !articles.length) {
    container.innerHTML = '<div class="loading-msg">No articles found.</div>';
    return;
  }
  container.innerHTML = articles.map(a => articleCardHtml(a)).join('');
}

function articleCardHtml(a) {
  const title   = esc(a.title || '');
  const desc    = esc(a.description || '');
  const source  = esc(a.source?.name || 'News');
  const time    = formatTime(a.publishedAt);
  const emoji   = getEmoji(a.title || '');
  const dataAttr = `data-article='${JSON.stringify(a).replace(/'/g, "&#39;")}'`;

  return `
    <div class="article-card" ${dataAttr} onclick="openArticleFromCard(this)">
      ${a.urlToImage
        ? `<img class="card-img" src="${esc(a.urlToImage)}" alt="" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
        : ''}
      <div class="card-img-ph" style="${a.urlToImage ? 'display:none' : ''}">${emoji}</div>
      <div class="card-body">
        <div class="card-meta">
          <span class="card-source">${source}</span>
          <span class="card-time">${time}</span>
        </div>
        <h3 class="card-title">${title}</h3>
        <p class="card-desc">${desc}</p>
        <div class="card-actions">
          <button class="chip primary" onclick="event.stopPropagation();openTabFromCard(this.closest('.article-card'),'article')">📰 Read</button>
          <button class="chip" onclick="event.stopPropagation();openTabFromCard(this.closest('.article-card'),'brief')">📋 Brief</button>
          <button class="chip" onclick="event.stopPropagation();openTabFromCard(this.closest('.article-card'),'sowhat')">💡 So What?</button>
        </div>
      </div>
    </div>
  `;
}

function openArticleFromCard(cardEl) {
  const raw = cardEl.getAttribute('data-article');
  try {
    const article = JSON.parse(raw);
    openArticle(article);
  } catch {}
}

function openTabFromCard(cardEl, tab) {
  const raw = cardEl.getAttribute('data-article');
  try {
    const article = JSON.parse(raw);
    openArticle(article);
    setTimeout(() => switchModalTab(tab, document.querySelector(`.mtab[onclick*="'${tab}'"]`)), 120);
  } catch {}
}

function renderBriefList(container, articles) {
  if (!articles.length) { container.innerHTML = '<div class="loading-msg">No articles.</div>'; return; }
  container.innerHTML = articles.map((a, i) => `
    <div class="brief-row" data-article='${JSON.stringify(a).replace(/'/g,"&#39;")}' onclick="openTabFromBrief(this,'brief')">
      <div class="brief-num">${i + 1}</div>
      <div class="brief-info">
        <div class="brief-title">${esc(a.title)}</div>
        <div class="brief-source">${esc(a.source?.name||'')} · ${formatTime(a.publishedAt)}</div>
      </div>
      <button class="brief-btn" onclick="event.stopPropagation();openTabFromBrief(this.closest('.brief-row'),'brief')">Get Brief →</button>
    </div>
  `).join('');
}

function renderTimelineList(container, articles) {
  if (!articles.length) { container.innerHTML = '<div class="loading-msg">No articles.</div>'; return; }
  container.innerHTML = `<p style="color:var(--text3);font-size:0.88rem;margin-bottom:14px;">Select an article to see its story timeline:</p>` +
    articles.map(a => `
      <div class="brief-row" data-article='${JSON.stringify(a).replace(/'/g,"&#39;")}' onclick="loadTimelinePage(this)">
        <div class="brief-num">🕐</div>
        <div class="brief-info">
          <div class="brief-title">${esc(a.title)}</div>
          <div class="brief-source">${esc(a.source?.name||'')} · ${formatTime(a.publishedAt)}</div>
        </div>
        <button class="brief-btn">View →</button>
      </div>
    `).join('');
}

function openTabFromBrief(rowEl, tab) {
  const raw = rowEl.getAttribute('data-article');
  try {
    const article = JSON.parse(raw);
    openArticle(article);
    setTimeout(() => switchModalTab(tab, document.querySelector(`.mtab[onclick*="'${tab}'"]`)), 120);
  } catch {}
}

// ═══════════════════════════════════════
// GEOLOCATION — REAL REGIONAL NEWS
// ═══════════════════════════════════════

function detectLocationSilent() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    pos => reverseGeocode(pos.coords.latitude, pos.coords.longitude),
    () => {},
    { timeout: 8000 }
  );
}

async function reverseGeocode(lat, lng) {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=10`);
    const d = await res.json();
    const city = d.address?.city || d.address?.town || d.address?.village || d.address?.county || '';
    if (city) { userCity = city; }
  } catch {}
}

function detectLocation() {
  const bar = document.getElementById('locationBar');
  bar.innerHTML = `<div class="location-detecting"><div class="spinner"></div><span>Detecting location…</span></div>`;

  if (!navigator.geolocation) { showManualInput(); return; }

  navigator.geolocation.getCurrentPosition(
    async pos => {
      try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&zoom=10`);
        const d = await res.json();
        const city = d.address?.city || d.address?.town || d.address?.village || d.address?.county || '';
        if (city) { userCity = city; setLocationFound(city); }
        else showManualInput();
      } catch { showManualInput(); }
    },
    () => showManualInput(),
    { timeout: 9000 }
  );
}

function setLocationFound(city) {
  userCity = city;
  const bar = document.getElementById('locationBar');
  bar.innerHTML = `
    <div class="location-found">
      <span class="loc-badge">📍 ${esc(city)}</span>
      <span style="color:var(--text3);font-size:0.85rem;">Showing news for ${esc(city)}</span>
      <button class="btn btn-ghost btn-sm" onclick="showManualInput()">Change</button>
    </div>`;
  document.getElementById('localSubtitle').textContent = `Local headlines for ${city}`;
  loadLocalNews(city);
}

function showManualInput() {
  const bar = document.getElementById('locationBar');
  bar.innerHTML = `
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <span style="font-size:0.88rem;color:var(--text3);">Enter your city:</span>
      <input type="text" class="loc-input" id="cityInput" placeholder="e.g. Mumbai, Delhi, Bangalore" onkeydown="if(event.key==='Enter')setManualCity()"/>
      <button class="btn btn-primary btn-sm" onclick="setManualCity()">Get News</button>
    </div>`;
}

function setManualCity() {
  const val = document.getElementById('cityInput')?.value?.trim();
  if (!val) { showToast('Please enter a city name'); return; }
  setLocationFound(val);
}

function initLocalNews() {
  if (userCity) {
    setLocationFound(userCity);
  } else {
    detectLocation();
  }
}

async function loadLocalNews(city) {
  const c = document.getElementById('localArticles');
  c.innerHTML = skeletonHtml(4);
  try {
    const res = await fetch(`${API_BASE}/news/local?city=${encodeURIComponent(city)}&country=in`);
    const data = await res.json();
    renderGrid(c, data.articles || []);
    updateDiscussionSelect(data.articles || []);
  } catch {
    c.innerHTML = '<div class="loading-msg">Could not load local news.</div>';
  }
}

// ═══════════════════════════════════════
// ARTICLE MODAL
// ═══════════════════════════════════════

function openArticle(article) {
  currentArticle = article;
  loadedFeatures = {};

  const src = esc(article.source?.name || 'News');
  const title = esc(article.title || '');
  const time  = formatTime(article.publishedAt);
  const author = article.author ? `By ${esc(article.author)} · ` : '';

  document.getElementById('modalHeader').innerHTML = `
    ${article.urlToImage ? `<img class="modal-img" src="${esc(article.urlToImage)}" alt="" onerror="this.style.display='none'">` : ''}
    <div class="modal-source">${src}</div>
    <h2 class="modal-title">${title}</h2>
    <div class="modal-meta">${author}${time}</div>
  `;

  document.getElementById('articleFullContent').innerHTML =
    `<p>${esc(article.content || article.description || 'Full content not available. Click "Read Original" below.')}</p>`;

  document.getElementById('articleSourceLink').href = article.url || '#';

  // Reset tabs
  document.querySelectorAll('.mtab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.mpanel').forEach(p => p.classList.remove('active'));
  document.querySelector('.mtab').classList.add('active');
  document.getElementById('tab-article').classList.add('active');

  // Reset listen btn
  const lb = document.getElementById('listenBtn');
  lb.className = 'btn-listen';
  lb.innerHTML = '🔊 Listen';
  stopSpeech();

  // Sentiment
  analyzeSentimentDisplay(article.content || article.description || article.title || '');

  document.getElementById('articleModal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeArticleModal() {
  document.getElementById('articleModal').classList.remove('open');
  document.body.style.overflow = '';
  stopSpeech();
}

function closeModal(e) {
  if (e.target === document.getElementById('articleModal')) closeArticleModal();
}

function switchModalTab(tab, btn) {
  document.querySelectorAll('.mtab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.mpanel').forEach(p => p.classList.remove('active'));

  // Find the button by tab name if not passed
  if (!btn) btn = document.querySelector(`.mtab[onclick*="'${tab}'"]`);
  if (btn) btn.classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');

  if (!loadedFeatures[tab]) {
    loadedFeatures[tab] = true;
    switch(tab) {
      case 'brief':    loadSmartBrief(); break;
      case 'sowhat':   loadSoWhat(); break;
      case 'proscons': loadProsCons(); break;
      case 'quiz':     loadQuiz(); break;
      case 'timeline': loadTimelineModal(); break;
    }
  }
}

// ═══════════════════════════════════════
// AI FEATURES
// ═══════════════════════════════════════

async function aiPost(endpoint, extraFields = {}) {
  const body = {
    title: currentArticle.title,
    content: currentArticle.content || currentArticle.description || currentArticle.title,
    url: currentArticle.url || '',
    ...extraFields,
  };
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function loadSmartBrief() {
  const loading = document.getElementById('briefLoading');
  const content = document.getElementById('briefContent');
  loading.style.display = 'flex';
  content.style.display = 'none';

  try {
    const data = await aiPost('/ai/smart-brief');
    const bullets = data.bullets || [];
    content.innerHTML = `
      <div class="brief-points">
        ${bullets.map((b, i) => `
          <div class="bpoint" style="animation-delay:${i*0.08}s">
            <div class="bnum">${i+1}</div>
            <div class="btext">${esc(b)}</div>
          </div>
        `).join('')}
      </div>`;
  } catch (e) {
    content.innerHTML = `<div class="loading-msg">Could not generate brief. ${e.message}</div>`;
  } finally {
    loading.style.display = 'none';
    content.style.display = 'block';
  }
}

async function loadSoWhat() {
  const loading = document.getElementById('sowhatLoading');
  const content = document.getElementById('sowhatContent');
  loading.style.display = 'flex';
  content.style.display = 'none';

  try {
    const data = await aiPost('/ai/so-what');
    content.innerHTML = `
      <div class="sowhat-cards">
        <div class="sw-card">
          <div class="sw-label">📌 Why This Matters</div>
          <div class="sw-text">${esc(data.why_matters || '')}</div>
        </div>
        <div class="sw-card impact">
          <div class="sw-label">👥 Citizen Impact</div>
          <div class="sw-text">${esc(data.citizen_impact || '')}</div>
        </div>
        <div class="sw-card future">
          <div class="sw-label">🔮 Future Implications</div>
          <div class="sw-text">${esc(data.future_implications || '')}</div>
        </div>
      </div>`;
  } catch (e) {
    content.innerHTML = `<div class="loading-msg">Could not analyse impact. ${e.message}</div>`;
  } finally {
    loading.style.display = 'none';
    content.style.display = 'block';
  }
}

async function loadProsCons() {
  const loading = document.getElementById('prosconsLoading');
  const content = document.getElementById('prosconsContent');
  loading.style.display = 'flex';
  content.style.display = 'none';

  try {
    const data = await aiPost('/ai/pros-cons');
    const pros = data.pros || [];
    const cons = data.cons || [];
    content.innerHTML = `
      <div class="pc-grid">
        <div class="pc-col pros">
          <div class="pc-head">✅ Pros</div>
          ${pros.map(p => `<div class="pc-item"><span>${esc(p)}</span></div>`).join('')}
        </div>
        <div class="pc-col cons">
          <div class="pc-head">❌ Cons</div>
          ${cons.map(c => `<div class="pc-item"><span>${esc(c)}</span></div>`).join('')}
        </div>
      </div>`;
  } catch (e) {
    content.innerHTML = `<div class="loading-msg">Could not generate analysis. ${e.message}</div>`;
  } finally {
    loading.style.display = 'none';
    content.style.display = 'block';
  }
}

async function loadQuiz() {
  const loading = document.getElementById('quizLoading');
  const content = document.getElementById('quizContent');
  loading.style.display = 'flex';
  content.style.display = 'none';

  try {
    const data = await aiPost('/ai/quiz');
    const letters = ['A','B','C','D'];
    content.innerHTML = `
      <div class="quiz-wrap">
        <p style="font-size:0.72rem;font-weight:700;letter-spacing:0.5px;color:var(--text4);text-transform:uppercase;margin-bottom:10px;">Comprehension Quiz</p>
        <div class="quiz-q">${esc(data.question || '')}</div>
        <div class="quiz-opts">
          ${(data.options || []).map((opt, i) => `
            <div class="qopt" onclick="answerQuiz(${i},${data.correct_index},'${esc(data.explanation||'')}')">
              <div class="qletter">${letters[i]}</div>
              <div class="qtext">${esc(opt)}</div>
            </div>
          `).join('')}
        </div>
        <div class="quiz-exp" id="quizExp"><strong>Explanation:</strong> ${esc(data.explanation || '')}</div>
      </div>`;
  } catch (e) {
    content.innerHTML = `<div class="loading-msg">Could not generate quiz. ${e.message}</div>`;
  } finally {
    loading.style.display = 'none';
    content.style.display = 'block';
  }
}

function answerQuiz(sel, correct, explanation) {
  document.querySelectorAll('.qopt').forEach((el, i) => {
    el.style.pointerEvents = 'none';
    if (i === correct) el.classList.add('correct');
    else if (i === sel) el.classList.add('incorrect');
  });
  const exp = document.getElementById('quizExp');
  if (exp) exp.classList.add('show');
  showToast(sel === correct ? '✅ Correct!' : '❌ Not quite — see explanation');
}

async function loadTimelineModal() {
  const loading = document.getElementById('timelineLoading');
  const content = document.getElementById('timelineContent');
  loading.style.display = 'flex';
  content.style.display = 'none';

  try {
    const data = await aiPost('/ai/timeline');
    const events = data.timeline || [];
    content.innerHTML = `
      <p style="font-size:0.8rem;color:var(--text4);margin-bottom:16px;">Story evolution for: <em>${esc(currentArticle.title.substring(0,60))}…</em></p>
      <div class="tl-modal-track">
        ${events.map(ev => `
          <div class="tl-event ${ev.significance === 'major' ? 'major' : ''}">
            <div class="tl-date">${esc(ev.date)}</div>
            <div class="tl-text">${esc(ev.event)}</div>
          </div>
        `).join('')}
      </div>`;
  } catch (e) {
    content.innerHTML = `<div class="loading-msg">Could not load timeline. ${e.message}</div>`;
  } finally {
    loading.style.display = 'none';
    content.style.display = 'block';
  }
}

async function loadTimelinePage(rowEl) {
  const raw = rowEl.getAttribute('data-article');
  let article;
  try { article = JSON.parse(raw); } catch { return; }
  currentArticle = article;

  const view = document.getElementById('timelineView');
  view.style.display = 'block';
  view.innerHTML = `<div class="panel-load"><div class="spinner"></div> Building timeline…</div>`;
  view.scrollIntoView({ behavior: 'smooth' });

  try {
    const data = await aiPost('/ai/timeline');
    const events = data.timeline || [];
    view.innerHTML = `
      <div class="tl-heading">🕐 ${esc(article.title)}</div>
      <div class="tl-track">
        ${events.map(ev => `
          <div class="tl-event ${ev.significance === 'major' ? 'major' : ''}">
            <div class="tl-date">${esc(ev.date)}</div>
            <div class="tl-text">${esc(ev.event)}</div>
          </div>
        `).join('')}
      </div>
      <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border);">
        <button class="btn btn-ghost btn-sm" onclick="openArticle(JSON.parse(this.closest('.timeline-view').dataset.art))">📰 Read article</button>
      </div>`;
    view.dataset.art = JSON.stringify(article);
  } catch (e) {
    view.innerHTML = `<div class="loading-msg">Could not build timeline. ${e.message}</div>`;
  }
}

async function analyzeSentimentDisplay(text) {
  try {
    const res = await fetch(`${API_BASE}/ai/sentiment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: currentArticle?.title || '', content: text }),
    });
    const data = await res.json();
    const badge = document.getElementById('sentimentBadge');
    if (badge) {
      badge.className = `sent-badge ${(data.label||'neutral').toLowerCase()}`;
      badge.textContent = `${data.label} tone`;
    }
  } catch {}
}

// ═══════════════════════════════════════
// TEXT-TO-SPEECH
// ═══════════════════════════════════════

async function toggleListen() {
  if (isSpeaking) { stopSpeech(); return; }

  const btn = document.getElementById('listenBtn');
  btn.innerHTML = '⏳ Loading…';
  btn.disabled = true;

  const text = currentArticle
    ? `${currentArticle.title}. ${currentArticle.content || currentArticle.description || ''}`
    : '';

  if (!text.trim()) {
    showToast('No content to read');
    btn.disabled = false;
    btn.innerHTML = '🔊 Listen';
    return;
  }

  // Always use browser TTS (Groq has no TTS)
  useBrowserTTS(text.substring(0, 3000), btn);
}

function useBrowserTTS(text, btn) {
  if (!('speechSynthesis' in window)) {
    showToast('Text-to-speech not supported in this browser');
    btn.disabled = false;
    btn.innerHTML = '🔊 Listen';
    return;
  }

  speechSynthesis.cancel();
  currentUtterance = new SpeechSynthesisUtterance(text);
  currentUtterance.rate = 0.95;
  currentUtterance.pitch = 1;

  currentUtterance.onstart = () => {
    isSpeaking = true;
    btn.className = 'btn-listen playing';
    btn.innerHTML = '⏹ Stop';
    btn.disabled = false;
    showToast('🔊 Reading aloud…');
  };

  currentUtterance.onend = currentUtterance.onerror = () => {
    isSpeaking = false;
    btn.className = 'btn-listen';
    btn.innerHTML = '🔊 Listen';
    btn.disabled = false;
  };

  speechSynthesis.speak(currentUtterance);
}

function stopSpeech() {
  isSpeaking = false;
  if (speechSynthesis) speechSynthesis.cancel();
  const btn = document.getElementById('listenBtn');
  if (btn) { btn.className = 'btn-listen'; btn.innerHTML = '🔊 Listen'; btn.disabled = false; }
}

// ═══════════════════════════════════════
// SEARCH
// ═══════════════════════════════════════

function switchSearchTab(tab) {
  document.querySelectorAll('.stab').forEach(t => t.classList.remove('active'));
  document.getElementById('keywordSearch').style.display = tab === 'keyword' ? 'block' : 'none';
  document.getElementById('urlSearch').style.display = tab === 'url' ? 'block' : 'none';
  document.getElementById(`tab${tab.charAt(0).toUpperCase()+tab.slice(1)}`).classList.add('active');
}

async function performSearch() {
  const q = document.getElementById('searchInput').value.trim();
  if (!q) { showToast('Enter a search term'); return; }
  const c = document.getElementById('searchResults');
  c.innerHTML = skeletonHtml(4);
  try {
    const res = await fetch(`${API_BASE}/news/search?query=${encodeURIComponent(q)}`);
    const data = await res.json();
    renderGrid(c, data.articles || []);
    showToast(`Found ${data.count || 0} articles`);
  } catch (e) {
    c.innerHTML = `<div class="loading-msg">Search failed: ${e.message}</div>`;
  }
}

async function fetchFromUrl() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url.startsWith('http')) { showToast('Enter a valid URL'); return; }
  const c = document.getElementById('searchResults');
  c.innerHTML = `<div class="loading-msg"><div class="spinner" style="margin:0 auto 12px;"></div>Fetching article…</div>`;
  try {
    const res = await fetch(`${API_BASE}/news/from-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();
    if (data.article) { renderGrid(c, [data.article]); showToast('Article fetched!'); }
    else c.innerHTML = '<div class="loading-msg">Could not extract article from that URL.</div>';
  } catch (e) {
    c.innerHTML = `<div class="loading-msg">Fetch failed: ${e.message}</div>`;
  }
}

// ═══════════════════════════════════════
// COMMUNITY
// ═══════════════════════════════════════

async function fetchGuidelines() {
  try {
    const res = await fetch(`${API_BASE}/discussions/guidelines`);
    const data = await res.json();
    const el = document.getElementById('guidelinesList');
    if (el && data.guidelines) {
      el.innerHTML = data.guidelines.map(g => `<li>${esc(g)}</li>`).join('');
    }
  } catch {}
}

function updateDiscussionSelect(articles) {
  const sel = document.getElementById('discussionArticleSelect');
  if (!sel) return;
  const existing = Array.from(sel.options).map(o => o.value);
  articles.forEach(a => {
    const val = a.url || a.title;
    if (!existing.includes(val)) {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = (a.title || '').substring(0, 90);
      sel.appendChild(opt);
      existing.push(val);
    }
  });
}

async function loadDiscussion() {
  const sel = document.getElementById('discussionArticleSelect');
  const panel = document.getElementById('discussionPanel');
  if (!sel.value) { panel.style.display = 'none'; return; }
  panel.style.display = 'block';
  const cl = document.getElementById('commentsList');
  cl.innerHTML = '<div class="loading-msg"><div class="spinner" style="margin:0 auto;"></div></div>';
  try {
    const res = await fetch(`${API_BASE}/discussions?article_url=${encodeURIComponent(sel.value)}`);
    const data = await res.json();
    renderComments(data.comments || []);
  } catch {
    cl.innerHTML = '<div class="no-comments">Could not load comments.</div>';
  }
}

function renderComments(comments) {
  const list = document.getElementById('commentsList');
  if (!comments.length) { list.innerHTML = '<div class="no-comments">No comments yet — be first!</div>'; return; }
  list.innerHTML = comments.map(c => `
    <div class="cmt-card">
      <div class="cmt-meta">
        <span class="cmt-user">👤 ${esc(c.username || 'Anonymous')}</span>
        <span class="cmt-time">${formatTime(c.timestamp)}</span>
      </div>
      <div class="cmt-text">${esc(c.text)}</div>
      <button class="cmt-like" onclick="likeComment('${c.id}',this)">❤️ ${c.likes || 0}</button>
    </div>
  `).join('');
}

async function submitComment() {
  const sel = document.getElementById('discussionArticleSelect');
  const username = document.getElementById('commentUsername').value.trim() || 'Anonymous';
  const text = document.getElementById('commentText').value.trim();
  if (!sel.value) { showToast('Select an article first'); return; }
  if (!text) { showToast('Write a comment first'); return; }

  try {
    const res = await fetch(`${API_BASE}/discussions/comment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_url: sel.value, username, text }),
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById('commentText').value = '';
      document.getElementById('charCount').textContent = '0 / 2000';
      showToast('Comment posted!');
      loadDiscussion();
    } else {
      showToast('Error: ' + (data.detail || data.error || 'Could not post'));
    }
  } catch (e) { showToast('Failed: ' + e.message); }
}

async function likeComment(id, btn) {
  const sel = document.getElementById('discussionArticleSelect');
  if (!sel.value) return;
  try {
    const res = await fetch(`${API_BASE}/discussions/like`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_url: sel.value, comment_id: id }),
    });
    const data = await res.json();
    if (data.success) { btn.textContent = `❤️ ${data.likes}`; btn.style.color = 'var(--red)'; }
  } catch {}
}

function updateCharCount() {
  const t = document.getElementById('commentText');
  const c = document.getElementById('charCount');
  if (t && c) c.textContent = `${t.value.length} / 2000`;
}

function openDiscussionFromModal() {
  const art = currentArticle;
  closeArticleModal();
  showSection('community');
  setTimeout(() => {
    const sel = document.getElementById('discussionArticleSelect');
    if (sel && art) {
      const opt = Array.from(sel.options).find(o => o.value === art.url || o.value === art.title);
      if (opt) { sel.value = opt.value; loadDiscussion(); }
    }
  }, 300);
}

// ═══════════════════════════════════════
// CHATBOT — grounded in live news
// ═══════════════════════════════════════

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
}

function sendSuggestion(btn) {
  document.getElementById('chatInput').value = btn.textContent.trim();
  sendChatMessage();
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  appendMsg('user', msg);
  input.value = '';
  input.style.height = 'auto';

  const sendBtn = document.getElementById('chatSendBtn');
  sendBtn.disabled = true;

  const typingId = 'typing-' + Date.now();
  appendTyping(typingId);

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, history: chatHistory, news_context: '' }),
    });
    const data = await res.json();
    const reply = data.response || 'Sorry, I could not process that.';

    chatHistory.push({ role: 'user', content: msg });
    chatHistory.push({ role: 'assistant', content: reply });
    if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);

    document.getElementById(typingId)?.remove();
    appendMsg('bot', reply);
  } catch (e) {
    document.getElementById(typingId)?.remove();
    appendMsg('bot', 'Connection error. Please check the backend is running.');
  } finally {
    sendBtn.disabled = false;
  }
}

function appendMsg(role, text) {
  const msgs = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `chat-msg ${role === 'user' ? 'user-msg' : 'bot-msg'}`;
  div.innerHTML = `
    <div class="msg-avatar">${role === 'user' ? 'You' : '🤖'}</div>
    <div class="msg-bubble">${esc(text).replace(/\n/g, '<br>')}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function appendTyping(id) {
  const msgs = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.id = id;
  div.className = 'chat-msg bot-msg';
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble"><div class="typing-dots"><div class="tdot"></div><div class="tdot"></div><div class="tdot"></div></div></div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

// ═══════════════════════════════════════
// UTILITY
// ═══════════════════════════════════════

function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function formatTime(d) {
  if (!d) return '';
  try {
    const date = new Date(d);
    const diff = Date.now() - date;
    const hrs  = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (hrs < 1)  return 'Just now';
    if (hrs < 24) return `${hrs}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString('en-IN', { day:'numeric', month:'short' });
  } catch { return d; }
}

function getEmoji(title) {
  const t = (title||'').toLowerCase();
  if (t.includes('climate')||t.includes('environment')) return '🌍';
  if (t.includes('tech')||t.includes('ai')||t.includes('digital')) return '💻';
  if (t.includes('health')||t.includes('medical')) return '🏥';
  if (t.includes('sport')||t.includes('cricket')||t.includes('football')) return '⚽';
  if (t.includes('economy')||t.includes('market')||t.includes('finance')) return '📈';
  if (t.includes('politic')||t.includes('election')||t.includes('government')) return '🏛️';
  if (t.includes('science')||t.includes('research')) return '🔬';
  if (t.includes('energy')||t.includes('solar')) return '⚡';
  if (t.includes('education')||t.includes('school')) return '📚';
  return '📰';
}

function skeletonHtml(n) {
  return `<div class="skeleton-wrap">${Array(n).fill('<div class="skeleton-card"></div>').join('')}</div>`;
}

let _toastTimer;
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.classList.remove('show'), 3000);
}
