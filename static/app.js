const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || '') ? u : '');
const fmt = (n) => (n == null ? '—' : n.toLocaleString('es-ES'));
const SOURCES = { wallapop: 'Wallapop', autoscout24: 'AutoScout24', cochesnet: 'coches.net', milanuncios: 'Milanuncios', flexicar: 'Flexicar', autocasion: 'Autocasion' };
const BODIES = { berlina: 'Berlina', familiar: 'Familiar', suv: 'SUV', monovolumen: 'Monovolumen' };
let LISTINGS = [], CONFIG = null, selectedBudgets = new Set();
let VIEW = localStorage.getItem('view') === 'list' ? 'list' : 'cards';

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function load() {
  [LISTINGS, CONFIG] = await Promise.all([api('/api/listings'), api('/api/config')]);
  if (!selectedBudgets.size) CONFIG.budgets.forEach((b, i) => b.active && selectedBudgets.add(i));
  renderBudgetChips(); fillSelects(); render();
}

function renderBudgetChips() {
  $('#budget-chips').innerHTML = CONFIG.budgets.map((b, i) =>
    `<span class="chip ${selectedBudgets.has(i) ? 'on' : ''}" data-i="${i}">${esc(b.name)} · ${fmt(b.min)}–${fmt(b.max)} €</span>`).join('');
  $('#budget-chips').querySelectorAll('.chip').forEach((c) => c.onclick = () => {
    const i = +c.dataset.i; selectedBudgets.has(i) ? selectedBudgets.delete(i) : selectedBudgets.add(i);
    renderBudgetChips(); render();
  });
}

function fillSelects() {
  const uniq = (k) => [...new Set(LISTINGS.map((l) => l[k]).filter(Boolean))].sort();
  const fill = (sel, vals, label) => {
    const cur = $(sel).value;
    $(sel).innerHTML = `<option value="">${label}</option>` + vals.map((v) => `<option value="${esc(v)}">${esc(SOURCES[v] || BODIES[v] || v)}</option>`).join('');
    $(sel).value = cur;
  };
  fill('#f-source', uniq('source'), 'Todos los portales');
  fill('#f-fuel', uniq('fuel'), 'Cualquier combustible');
  fill('#f-body', uniq('body'), 'Toda carrocería');
}

function filtered() {
  const text = $('#f-text').value.toLowerCase(), src = $('#f-source').value, fuel = $('#f-fuel').value, body = $('#f-body').value;
  const maxkm = +$('#f-maxkm').value || Infinity, minyear = +$('#f-minyear').value || 0, deals = $('#f-deals').checked;
  const budgets = [...selectedBudgets].map((i) => CONFIG.budgets[i]);
  let out = LISTINGS.filter((l) =>
    (!budgets.length || budgets.some((b) => l.price >= b.min && l.price <= b.max)) &&
    (!text || (l.title || '').toLowerCase().includes(text)) &&
    (!src || l.source === src) && (!fuel || l.fuel === fuel) && (!body || l.body === body) &&
    (l.km ?? 0) <= maxkm && (l.year ?? 9999) >= minyear && (!deals || l.is_deal));
  const S = {
    price_asc: (a, b) => (a.price ?? 1e9) - (b.price ?? 1e9),
    discount_desc: (a, b) => (b.discount_pct ?? -99) - (a.discount_pct ?? -99),
    payback_asc: (a, b) => (a.payback_months ?? 999) - (b.payback_months ?? 999),
    km_asc: (a, b) => (a.km ?? 1e9) - (b.km ?? 1e9),
    year_desc: (a, b) => (b.year ?? 0) - (a.year ?? 0),
    recent: (a, b) => (b.first_seen || '').localeCompare(a.first_seen || ''),
  };
  return out.sort(S[$('#f-sort').value]);
}

function render() {
  const rows = filtered();
  const deals = rows.filter((r) => r.is_deal).length;
  const avg = rows.length ? Math.round(rows.reduce((s, r) => s + r.price, 0) / rows.length) : null;
  const best = rows.reduce((m, r) => (r.payback_months && (!m || r.payback_months < m) ? r.payback_months : m), null);
  $('#stats').innerHTML = `
    <div class="stat"><b>${fmt(rows.length)}</b><span>Coches encontrados</span></div>
    <div class="stat hot"><b>${deals}</b><span>Gangas detectadas 🔥</span></div>
    <div class="stat"><b>${fmt(avg)} €</b><span>Precio medio</span></div>
    <div class="stat"><b>${best ?? '—'} m</b><span>Mejor payback GetAround</span></div>`;
  $('#empty').classList.toggle('hidden', rows.length > 0);
  const cardHtml = (l) => `
    <article class="card ${l.is_deal ? 'deal' : ''}" data-id="${esc(l.id)}" id="car-${l.id.replace(/[^a-z0-9]/gi, '-')}" tabindex="0">
      <div class="thumb" style="background-image:url('${encodeURI(safeUrl(l.image))}')">
        <button type="button" class="hide-btn" data-hide="${esc(l.id)}" title="Ocultar: coche dañado o no me interesa" aria-label="Ocultar anuncio">🚫</button>
        <span class="badge src">${esc(SOURCES[l.source] || l.source)}</span>
        ${l.is_deal ? `<span class="badge hot">🔥 -${l.discount_pct}%</span>` : ''}
        <div class="overlay">
          <span class="pill">📅 ${l.year ?? '—'}</span>
          <span class="pill">🛣 ${fmt(l.km)} km</span>
          ${l.images.length > 1 ? `<span class="pill photos">📷 ${l.images.length}</span>` : ''}
        </div>
      </div>
      <div class="body">
        <div class="title">${esc(l.title || `${l.make} ${l.model}`)}</div>
        <div class="price">${fmt(l.price)} €${l.median_price ? `<small>mediana ${fmt(l.median_price)} €</small>` : ''}</div>
        <div class="specs"><span>🚘 ${BODIES[l.body] || '—'}</span><span>⛽ ${esc(l.fuel || '—')}</span><span>📍 ${esc(l.location || '—')}${l.copies ? ` <em class="copies" title="También en: ${esc((l.also_in || []).join(', '))}">+${l.copies}</em>` : ''}</span></div>
        <div class="roi"><span>Beneficio <b>${fmt(l.monthly_profit)} €/mes</b></span><span>Payback <b>${l.payback_months ?? '—'} m</b></span></div>
        <a class="btn primary small go-link" href="${esc(safeUrl(l.url) || '#')}" target="_blank" rel="noopener noreferrer">Ver en ${esc(SOURCES[l.source] || 'la web')} ↗</a>
      </div>
    </article>`;
  const rowHtml = (l) => `
    <article class="row ${l.is_deal ? 'deal' : ''}" data-id="${esc(l.id)}" tabindex="0">
      <div class="r-thumb" style="background-image:url('${encodeURI(safeUrl(l.image))}')"></div>
      <div class="r-main">
        <div class="title">${l.is_deal ? '🔥 ' : ''}${esc(l.title || `${l.make} ${l.model}`)}</div>
        <div class="specs"><span>${esc(SOURCES[l.source] || l.source)}</span><span>📅 ${l.year ?? '—'}</span><span>🛣 ${fmt(l.km)} km</span>
          <span>⛽ ${esc(l.fuel || '—')}</span><span>📍 ${esc(l.location || '—')}${l.copies ? ` <em class="copies" title="También en: ${esc((l.also_in || []).join(', '))}">+${l.copies}</em>` : ''}</span></div>
      </div>
      <div class="r-price"><b>${fmt(l.price)} €</b>${l.is_deal ? `<small>-${l.discount_pct}% vs mediana</small>` : (l.median_price ? `<small>mediana ${fmt(l.median_price)} €</small>` : '')}</div>
      <div class="r-roi"><span>Beneficio <b>${fmt(l.monthly_profit)} €/mes</b></span><span>Payback <b>${l.payback_months ?? '—'} m</b></span></div>
      <div class="r-actions">
        <a class="btn primary small go-link" href="${esc(safeUrl(l.url) || '#')}" target="_blank" rel="noopener noreferrer">Ver ↗</a>
        <button type="button" class="hide-btn" data-hide="${esc(l.id)}" title="Ocultar: coche dañado o no me interesa" aria-label="Ocultar anuncio">🚫</button>
      </div>
    </article>`;
  $('#grid').className = VIEW === 'list' ? 'list' : 'grid';
  $('#grid').innerHTML = rows.slice(0, 300).map(VIEW === 'list' ? rowHtml : cardHtml).join('');
  document.querySelectorAll('#view-toggle button').forEach((b) => b.classList.toggle('on', b.dataset.view === VIEW));
  $('#grid').querySelectorAll('[data-id]').forEach((c) => c.onclick = () => openDetail(c.dataset.id));
  $('#grid').querySelectorAll('.go-link').forEach((a) => a.onclick = (e) => e.stopPropagation());
  $('#grid').querySelectorAll('.hide-btn').forEach((b) => b.onclick = async (e) => {
    e.stopPropagation();
    try { await api(`/api/listings/${encodeURIComponent(b.dataset.hide)}/hide`, { method: 'POST' }); } catch { return; }
    LISTINGS = LISTINGS.filter((x) => x.id !== b.dataset.hide); render();
  });
}

// ---- Ficha del anuncio con galería ----
let DETAIL = null, PHOTO = 0;
function showPhoto(i) {
  const imgs = DETAIL.images;
  PHOTO = (i + imgs.length) % imgs.length;
  $('#d-img').src = safeUrl(imgs[PHOTO]);
  $('#d-counter').textContent = `${PHOTO + 1} / ${imgs.length}`;
  $('#d-thumbs').querySelectorAll('img').forEach((t, j) => t.classList.toggle('on', j === PHOTO));
  const multi = imgs.length > 1;
  ['#d-prev', '#d-next', '#d-counter'].forEach((s) => $(s).classList.toggle('hidden', !multi));
}
function openDetail(id) {
  const l = LISTINGS.find((x) => x.id === id); if (!l) return;
  DETAIL = { ...l, images: l.images.length ? l.images : [l.image] };
  $('#d-thumbs').innerHTML = DETAIL.images.length > 1 ? DETAIL.images.map((u, j) => `<img src="${esc(safeUrl(u))}" data-j="${j}" loading="lazy" alt="Miniatura ${j + 1}" />`).join('') : '';
  $('#d-thumbs').querySelectorAll('img').forEach((t) => t.onclick = () => showPhoto(+t.dataset.j));
  $('#d-source').textContent = SOURCES[l.source] || l.source;
  $('#d-title').textContent = l.title || `${l.make} ${l.model}`;
  $('#d-location').textContent = `📍 ${l.location || 'Ubicación no indicada'}${l.also_in?.length ? ` · también en ${l.also_in.join(', ')}` : ''}`;
  $('#d-price').innerHTML = `${fmt(l.price)} €${l.is_deal ? '<span class="badge hot static">🔥 Ganga</span>' : ''}`;
  $('#d-year').textContent = l.year ?? '—';
  $('#d-km').textContent = `${fmt(l.km)} km`;
  $('#d-body').textContent = BODIES[l.body] || '—';
  $('#d-fuel').textContent = l.fuel || '—';
  $('#d-gear').textContent = l.gearbox || '—';
  $('#d-profit').textContent = `${fmt(l.monthly_profit)} €`;
  $('#d-payback').textContent = l.payback_months ? `${l.payback_months} meses` : '—';
  $('#d-disc').textContent = l.discount_pct != null ? `${l.discount_pct > 0 ? '-' : '+'}${Math.abs(l.discount_pct)}%` : 'Sin datos';
  $('#d-link').href = safeUrl(l.url) || '#';
  showPhoto(0);
  $('#detail').showModal();
  $('#detail').scrollTop = 0;
}
$('#d-prev').onclick = () => showPhoto(PHOTO - 1);
$('#d-next').onclick = () => showPhoto(PHOTO + 1);
$('#detail-close').onclick = () => $('#detail').close();
$('#detail').addEventListener('click', (e) => { if (e.target.id === 'detail') $('#detail').close(); });
document.addEventListener('keydown', (e) => {
  if (!$('#detail').open) return;
  if (e.key === 'ArrowLeft') showPhoto(PHOTO - 1);
  if (e.key === 'ArrowRight') showPhoto(PHOTO + 1);
});

async function refreshStatus() {
  if (document.hidden) return;
  let s;
  try { s = await api('/api/status'); } catch { $('#status').textContent = 'Sin conexión'; return; }
  const el = $('#status');
  el.classList.toggle('running', s.running);
  el.textContent = s.running ? 'Buscando…' : s.last_run ? `Última: ${s.last_run.slice(11, 16)} · +${s.last_new} nuevos` : 'Sin búsquedas aún';
  $('#btn-scrape').disabled = s.running;
  if (refreshStatus.wasRunning && !s.running) load();
  refreshStatus.wasRunning = s.running;
  $('#tg-state').textContent = s.telegram ? '✅ Telegram configurado. Recibirás las gangas.' : '⚠️ Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en el archivo .env y reinicia.';
}

// ---- Ajustes ----
function budgetLine(b = { name: '', min: 0, max: 0, active: true }) {
  const d = document.createElement('div'); d.className = 'budget-line';
  d.innerHTML = `<input type="checkbox" ${b.active ? 'checked' : ''} /><input type="text" value="${esc(b.name)}" placeholder="Nombre" />
    <input type="number" value="${b.min}" placeholder="Mín €" /><input type="number" value="${b.max}" placeholder="Máx €" />
    <button type="button" class="btn ghost small">✕</button>`;
  d.querySelector('button').onclick = () => d.remove();
  return d;
}
function openSettings() {
  const ed = $('#budget-editor'); ed.innerHTML = ''; CONFIG.budgets.forEach((b) => ed.appendChild(budgetLine(b)));
  $('#s-age').value = CONFIG.max_age_years; $('#s-km').value = CONFIG.max_km; $('#s-deal').value = CONFIG.deal_threshold_pct;
  $('#s-hours').value = CONFIG.economics.rented_hours_month; $('#s-comm').value = CONFIG.economics.getaround_commission_pct;
  $('#s-costs').value = CONFIG.economics.monthly_fixed_costs;
  $('#s-canarias').checked = CONFIG.exclude_canarias !== false;
  $('#s-sources').innerHTML = Object.entries(SOURCES).map(([k, v]) => `<span class="chip ${CONFIG.sources.includes(k) ? 'on' : ''}" data-k="${k}">${v}</span>`).join('');
  $('#s-sources').querySelectorAll('.chip').forEach((c) => c.onclick = () => c.classList.toggle('on'));
  $('#s-bodies').innerHTML = Object.entries(BODIES).map(([k, v]) => `<span class="chip ${CONFIG.body_types.includes(k) ? 'on' : ''}" data-k="${k}">${v}</span>`).join('');
  $('#s-bodies').querySelectorAll('.chip').forEach((c) => c.onclick = () => c.classList.toggle('on'));
  $('#settings').showModal();
}
async function saveSettings() {
  const budgets = [...document.querySelectorAll('.budget-line')].map((d) => {
    const [chk, name, min, max] = d.querySelectorAll('input');
    return { active: chk.checked, name: name.value || 'Presupuesto', min: +min.value, max: +max.value };
  });
  try {
  CONFIG = await api('/api/config', { method: 'PUT', body: JSON.stringify({
    ...CONFIG, budgets, max_age_years: +$('#s-age').value, max_km: +$('#s-km').value, deal_threshold_pct: +$('#s-deal').value, exclude_canarias: $('#s-canarias').checked,
    sources: [...document.querySelectorAll('#s-sources .chip.on')].map((c) => c.dataset.k),
    body_types: [...document.querySelectorAll('#s-bodies .chip.on')].map((c) => c.dataset.k),
    economics: { rented_hours_month: +$('#s-hours').value, getaround_commission_pct: +$('#s-comm').value, monthly_fixed_costs: +$('#s-costs').value },
  }) });
  } catch { alert('Configuración no válida. Revisa los valores.'); return; }
  selectedBudgets.clear(); $('#settings').close(); load();
}

$('#btn-scrape').onclick = async () => { await api('/api/scrape', { method: 'POST' }); refreshStatus(); };
$('#btn-settings').onclick = openSettings;
$('#add-budget').onclick = () => $('#budget-editor').appendChild(budgetLine());
$('#save-settings').onclick = saveSettings;
$('#tg-test').onclick = async () => { const r = await api('/api/telegram/test', { method: 'POST' }); alert(r.ok ? 'Mensaje enviado ✅' : 'No se pudo enviar. Revisa el .env'); };
let t; const deb = () => { clearTimeout(t); t = setTimeout(render, 200); };
['#f-text', '#f-source', '#f-fuel', '#f-body', '#f-maxkm', '#f-minyear', '#f-sort', '#f-deals'].forEach((s) => $(s).addEventListener('input', deb));

// ---- Vista tarjetas / lista ----
document.querySelectorAll('#view-toggle button').forEach((b) => b.onclick = () => {
  VIEW = b.dataset.view; localStorage.setItem('view', VIEW); render();
});

// ---- Pestañas ----
document.querySelectorAll('.tab').forEach((t) => t.onclick = () => {
  document.querySelectorAll('.tab').forEach((x) => x.classList.toggle('on', x === t));
  $('#tab-cars').classList.toggle('hidden', t.dataset.tab !== 'cars');
  $('#tab-prices').classList.toggle('hidden', t.dataset.tab !== 'prices');
  if (t.dataset.tab === 'prices') loadModels();
});

// ---- Precios por modelo ----
let MODELS = [];
async function loadModels() {
  try { MODELS = await api('/api/models'); } catch { MODELS = []; }
  fillModels();
}
function fillModels() {
  const q = $('#p-search').value.trim().toLowerCase(), cur = $('#p-model').value;
  const list = MODELS.filter((m) => !q || m.label.toLowerCase().includes(q)).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  $('#p-model').innerHTML = list.map((m) =>
    `<option value="${esc(m.key)}">${esc(m.label)} · ${m.count} ${m.count === 1 ? 'anuncio' : 'anuncios'} · desde ${fmt(m.min_price)} €</option>`).join('')
    || '<option value="">Sin modelos</option>';
  if (list.some((m) => m.key === cur)) $('#p-model').value = cur;
  loadPrices();
}

const dayLabel = (d) => new Date(d + 'T00:00:00').toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });

function lineChart(points) {
  const W = 720, H = 260, L = 56, R = 16, T = 14, B = 30;
  const t = (d) => new Date(d + 'T00:00:00').getTime();
  const xs = points.map((p) => t(p.day)), x0 = Math.min(...xs), x1 = Math.max(...xs);
  const vals = points.flatMap((p) => [p.min_price, p.median_price]);
  let lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = Math.max((hi - lo) * 0.15, hi * 0.03); lo = Math.max(0, lo - pad); hi += pad;
  const X = (d) => (x1 === x0 ? (L + W - R) / 2 : L + ((t(d) - x0) / (x1 - x0)) * (W - L - R));
  const Y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const ticks = [0, 1, 2, 3].map((i) => lo + ((hi - lo) * i) / 3);
  const path = (k) => points.map((p, i) => `${i ? 'L' : 'M'}${X(p.day).toFixed(1)},${Y(p[k]).toFixed(1)}`).join('');
  const dots = (k, cls, label) => points.map((p) =>
    `<circle class="${cls}" cx="${X(p.day).toFixed(1)}" cy="${Y(p[k]).toFixed(1)}" r="4"><title>${esc(dayLabel(p.day))} · ${label}: ${fmt(p[k])} €</title></circle>`).join('');
  const xl = points.length > 1 ? [points[0], points[points.length - 1]] : [points[0]];
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
    ${ticks.map((v) => `<line class="grid-line" x1="${L}" x2="${W - R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/><text class="axis" x="${L - 8}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${fmt(Math.round(v / 10) * 10)} €</text>`).join('')}
    ${xl.map((p, i) => `<text class="axis" x="${X(p.day).toFixed(1)}" y="${H - 8}" text-anchor="${points.length === 1 ? 'middle' : i ? 'end' : 'start'}">${esc(dayLabel(p.day))}</text>`).join('')}
    ${points.length > 1 ? `<path class="l-med" d="${path('median_price')}"/><path class="l-min" d="${path('min_price')}"/>` : ''}
    ${dots('median_price', 'd-med', 'mediana')}${dots('min_price', 'd-min', 'más barato')}
  </svg>
  <div class="chart-legend"><span><i style="background:var(--accent2)"></i>Precio más barato</span><span><i style="background:var(--accent)"></i>Precio mediano</span></div>`;
}

async function loadPrices() {
  const key = $('#p-model').value;
  if (!key) { $('#p-chart').innerHTML = ''; $('#p-kpis').innerHTML = ''; $('#p-cheapest').innerHTML = ''; $('#p-note').textContent = 'No hay modelos con anuncios todavía.'; return; }
  let d;
  try { d = await api(`/api/price-history?model=${encodeURIComponent(key)}`); } catch { $('#p-note').textContent = 'No se pudo cargar el histórico.'; return; }
  const pts = d.points;
  if (pts.length) {
    const last = pts[pts.length - 1], first = pts[0];
    const best = pts.reduce((m, p) => (p.min_price < m.min_price ? p : m), pts[0]);
    const delta = last.min_price - first.min_price, pct = first.min_price ? Math.round((delta / first.min_price) * 1000) / 10 : 0;
    const isNewLow = pts.length > 1 && last.min_price <= best.min_price && last.min_price < first.min_price;
    $('#p-kpis').innerHTML = `
      <div class="kpi"><span>Más barato hoy</span><b>${fmt(last.min_price)} €</b></div>
      <div class="kpi"><span>Mínimo histórico</span><b>${fmt(best.min_price)} €</b></div>
      <div class="kpi"><span>Cambio desde ${esc(dayLabel(first.day))}</span><b>${pts.length > 1 ? `${delta > 0 ? '+' : ''}${fmt(delta)} € (${pct}%)` : '—'}</b></div>
      <div class="kpi"><span>Anuncios únicos</span><b>${fmt(last.count)}</b></div>`;
    $('#p-chart').innerHTML = lineChart(pts);
    $('#p-note').textContent = isNewLow ? '🔥 ¡Hoy está en su precio más bajo registrado!'
      : pts.length < 2 ? 'Solo hay un día registrado: el gráfico se irá completando con cada día que se haga una búsqueda.' : '';
  } else {
    $('#p-kpis').innerHTML = ''; $('#p-chart').innerHTML = '';
    $('#p-note').textContent = 'Aún no hay histórico para este modelo: se guarda al terminar cada búsqueda.';
  }
  $('#p-cheapest').innerHTML = d.cheapest.map((c) => `
    <div class="cheap"><span>${esc(c.title)} · ${c.year ?? '—'} · ${fmt(c.km)} km · ${esc(c.location || '—')}</span>
      <b>${fmt(c.price)} €</b>
      <a class="btn ghost small" href="${esc(safeUrl(c.url) || '#')}" target="_blank" rel="noopener noreferrer">Ver en ${esc(SOURCES[c.source] || 'la web')} ↗</a></div>`).join('')
    || '<p class="muted">Sin anuncios actuales.</p>';
}
$('#p-model').addEventListener('change', loadPrices);
$('#p-search').addEventListener('input', fillModels);

load(); refreshStatus(); setInterval(refreshStatus, 4000);
