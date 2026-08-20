const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// DOM Elements
const query = $('#query');
const form = $('#query-form');
const button = $('#analyze');
const conversation = $('#conversation');
const welcome = $('#welcome');
const card = $('#result-card');
const upload = $('#file-input');
const mic = $('#mic-button');
const attachment = $('#attachment-button');
const pdf = $('#download-pdf');
const topbarPdf = $('#topbar-pdf-btn');

let landmark = null;
let currentTripId = null;
let latestPlanData = null;

const userId = sessionStorage.trippilotSessionId || (sessionStorage.trippilotSessionId = crypto.randomUUID());

function formatCurrency(val) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
}

function cleanText(val) {
  if (!val) return '';
  return String(val).replace(/\*\*/g, '').replace(/\*/g, '');
}

function addChat(who, text) {
  const item = document.createElement('div');
  item.className = `chat-bubble ${who}`;
  
  const sender = document.createElement('div');
  sender.className = 'chat-sender-tag';
  sender.innerHTML = who === 'user' ? '<span>YOU</span>' : '<span>TRIPPILOT AI COPILOT</span>';
  
  const body = document.createElement('div');
  body.textContent = cleanText(text);
  
  item.append(sender, body);
  conversation.append(item);
  item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// TAB SWITCHING
$$('.deck-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $$('.deck-tab').forEach((t) => t.classList.remove('active'));
    $$('.deck-pane').forEach((p) => p.classList.remove('active'));
    tab.classList.add('active');
    const target = $(`#pane-${tab.dataset.tab}`);
    if (target) target.classList.add('active');
  });
});

// PREFERENCE PILL TOGGLES
$$('#diet-toggles .pref-btn').forEach((pill) => {
  pill.addEventListener('click', () => {
    $$('#diet-toggles .pref-btn').forEach((p) => p.classList.remove('active'));
    pill.classList.add('active');
  });
});

$$('#crowd-toggles .pref-btn').forEach((pill) => {
  pill.addEventListener('click', () => {
    $$('#crowd-toggles .pref-btn').forEach((p) => p.classList.remove('active'));
    pill.classList.add('active');
  });
});

$('#reset-prefs')?.addEventListener('click', () => {
  $$('#diet-toggles .pref-btn').forEach((p, idx) => p.classList.toggle('active', idx === 0));
  $$('#crowd-toggles .pref-btn').forEach((p, idx) => p.classList.toggle('active', idx === 0));
});

// QUICK ACTION PROMPT CHIPS
$$('.btn-prompt-chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    query.value = chip.dataset.action;
    form.requestSubmit();
  });
});

// SCENARIO ITEMS (USER CLICKABLE)
$$('.scenario-item').forEach((item) => {
  item.addEventListener('click', () => {
    $$('.scenario-item').forEach((o) => o.classList.remove('active'));
    item.classList.add('active');
    query.value = item.dataset.query;
    form.requestSubmit();
  });
});

// DESTINATION CHIPS
$$('.btn-dest-chip').forEach((pill) => {
  pill.addEventListener('click', () => {
    const dest = pill.dataset.dest;
    query.value = `Plan a 4-day trip to ${dest} with vegetarian dining and low crowd recommendations.`;
    form.requestSubmit();
  });
});

// QUICK MEDIA BUTTONS
$$('[data-upload]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const kind = btn.dataset.upload;
    upload.accept = { image: 'image/*', audio: 'audio/*', video: 'video/*' }[kind] || 'image/*,audio/*,video/*';
    upload.click();
  });
});

attachment.addEventListener('click', () => {
  upload.accept = 'image/*,audio/*,video/*';
  upload.click();
});

// FILE UPLOAD HANDLER
upload.addEventListener('change', async () => {
  const file = upload.files[0];
  if (!file) return;
  const type = file.type.startsWith('image/')
    ? 'image'
    : file.type.startsWith('audio/')
    ? 'audio'
    : file.type.startsWith('video/')
    ? 'video'
    : 'image';

  const status = $('#upload-status');
  status.hidden = false;
  status.textContent = `Attached: ${file.name}`;

  const body = new FormData();
  body.append('file', file);

  try {
    const res = await fetch(`/v1/multimodal/${type}`, { method: 'POST', body });
    if (!res.ok) throw new Error();
    const data = await res.json();
    landmark = data.detected_landmark || file.name;
    status.textContent = `Attached: ${data.detected_landmark || file.name}`;
    if (data.extracted_prompt) {
      query.value = data.extracted_prompt;
      query.focus();
    }
  } catch {
    status.textContent = 'Could not process media.';
  }
});

// MICROPHONE VOICE INPUT
mic.addEventListener('click', () => {
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Speech) {
    alert('Voice input requires Web Speech API support (Google Chrome).');
    return;
  }
  const rec = new Speech();
  rec.lang = 'en-IN';
  rec.interimResults = true;
  mic.classList.add('recording');

  rec.onresult = (e) => {
    query.value = Array.from(e.results).map((r) => r[0].transcript).join('');
  };
  rec.onend = () => {
    mic.classList.remove('recording');
    if (query.value.trim()) form.requestSubmit();
  };
  rec.start();
});

// RENDER RESPONSE DATA
function renderResponseData(data) {
  latestPlanData = data;
  currentTripId = data.trip_id;

  // Badges
  $('#intent-badge').textContent = data.intent.replaceAll('_', ' ').toUpperCase();
  $('#model-badge').textContent = data.model_used.toUpperCase();
  $('#confidence-badge').textContent = `${Math.round(data.confidence * 100)}% CONFIDENCE`;

  // If this was a clarification question, show chat response only
  if (data.requires_clarification) {
    return;
  }

  welcome.hidden = true;
  card.hidden = false;
  topbarPdf.hidden = false;

  // Answer
  $('#answer').textContent = cleanText(data.answer);

  // Over-Budget Alert
  const bAlert = $('#budget-alert');
  if (data.budget && data.budget.is_over_budget) {
    bAlert.hidden = false;
    $('#overage-tag').textContent = `${formatCurrency(data.budget.overage_amount)} over`;
    const redList = $('#reduction-list');
    redList.innerHTML = '';
    (data.budget.reduction_suggestions || []).forEach((s, idx) => {
      const div = document.createElement('div');
      div.className = 'reduction-chip';
      div.innerHTML = `
        <span><b>${idx + 1}. ${s.action}</b> (${s.description})</span>
        <span class="reduction-save-text">Save ${formatCurrency(s.estimated_saving)}</span>
      `;
      redList.append(div);
    });
  } else {
    bAlert.hidden = true;
  }

  // Render Deck Cards
  renderFlightCards(data.flight_recommendations || []);
  renderHotelCards(data.hotel_recommendations || []);
  renderActivityCards(data.activity_recommendations || []);

  // Render Budget & Schedule
  if (data.budget) {
    renderBudgetTable(data.budget);
  }
  renderItineraryTimeline(data.itinerary_days || []);
  renderEvidenceSources(data.sources || []);
}

function renderFlightCards(flights) {
  const container = $('#flight-cards');
  container.innerHTML = '';
  if (!flights.length) {
    container.innerHTML = '<div style="color:#64748b;font-size:12.5px;">No flight options needed or matched.</div>';
    return;
  }
  flights.forEach((f) => {
    const card = document.createElement('div');
    card.className = 'rec-card';
    card.innerHTML = `
      <div class="rc-head">
        <div class="rc-title">${f.airline} ${f.flight_number}</div>
        <span class="rc-score-pill">${f.score}% Match</span>
      </div>
      <div class="rc-route">${f.origin} → ${f.destination} · ${f.departure_time} - ${f.arrival_time} (${f.duration})</div>
      <div class="rc-why-callout"><b>Why:</b> ${f.recommendation_reason}</div>
      <div class="rc-foot">
        <div class="rc-price">${formatCurrency(f.price.amount)}</div>
        <button class="btn-select-card" data-type="flight" data-id="${f.id}">Select Flight</button>
      </div>
    `;
    container.append(card);
  });
}

function renderHotelCards(hotels) {
  const container = $('#hotel-cards');
  container.innerHTML = '';
  if (!hotels.length) {
    container.innerHTML = '<div style="color:#64748b;font-size:12.5px;">No hotel accommodations needed or matched.</div>';
    return;
  }
  hotels.forEach((h) => {
    const card = document.createElement('div');
    card.className = 'rec-card';
    card.innerHTML = `
      <div class="rc-head">
        <div class="rc-title">${h.name}</div>
        <span class="rc-score-pill">${h.user_rating}/10 ★</span>
      </div>
      <div class="rc-route">${h.neighborhood}, ${h.city} · ${h.star_rating}★ (${h.cancellation_policy})</div>
      <div class="rc-why-callout"><b>Why:</b> ${h.recommendation_reason}</div>
      <div class="rc-foot">
        <div class="rc-price">${formatCurrency(h.price_per_night.amount)}/night</div>
        <button class="btn-select-card" data-type="hotel" data-id="${h.id}">Select Hotel</button>
      </div>
    `;
    container.append(card);
  });
}

function renderActivityCards(activities) {
  const container = $('#activity-cards');
  container.innerHTML = '';
  if (!activities.length) {
    container.innerHTML = '<div style="color:#64748b;font-size:12.5px;">No curated activities listed.</div>';
    return;
  }
  activities.forEach((a) => {
    const card = document.createElement('div');
    card.className = 'rec-card';
    card.innerHTML = `
      <div class="rc-head">
        <div class="rc-title">${a.name}</div>
        <span class="rc-score-pill">${a.rating} ★</span>
      </div>
      <div class="rc-route">${a.category} · Timing: ${a.best_time} · Crowd: ${a.crowd_level}</div>
      <div class="rc-why-callout"><b>Why:</b> ${a.recommendation_reason}</div>
      <div class="rc-foot">
        <div class="rc-price">${formatCurrency(a.price.amount)}</div>
        <button class="btn-select-card" data-type="activity" data-id="${a.id}">Add to Trip</button>
      </div>
    `;
    container.append(card);
  });
}

function renderBudgetTable(budget) {
  const tbody = $('#budget-rows');
  tbody.innerHTML = '';

  $('#stat-ceiling').textContent = budget.budget_ceiling ? formatCurrency(budget.budget_ceiling) : 'None';
  $('#stat-total').textContent = formatCurrency(budget.grand_total);
  
  const remEl = $('#stat-remaining');
  const remSub = $('#stat-remaining-sub');
  if (budget.remaining_budget !== null) {
    remEl.textContent = formatCurrency(budget.remaining_budget);
    remEl.className = budget.is_over_budget ? 'kpi-num' : 'kpi-num positive';
    remEl.style.color = budget.is_over_budget ? '#f43f5e' : '#10b981';
    if (remSub) remSub.textContent = budget.is_over_budget ? 'Over Budget Ceiling' : 'Safe Buffer Remaining';
  } else {
    remEl.textContent = 'N/A';
  }

  budget.categories.forEach((cat) => {
    cat.items.forEach((item, idx) => {
      const tr = document.createElement('tr');
      const catName = cat.category.replace('_', ' ').toUpperCase();
      tr.innerHTML = `
        <td>${idx === 0 ? `<b style="color:#93c5fd;">${catName}</b>` : ''}</td>
        <td>
          <div style="font-weight:600;">${item.name}</div>
          ${item.notes ? `<div style="font-size:11.5px;color:#94a3b8;margin-top:2px;">${item.notes}</div>` : ''}
        </td>
        <td style="text-align:center;">${item.quantity}</td>
        <td style="text-align:right; font-family:'JetBrains Mono',monospace;">${formatCurrency(item.unit_price)}</td>
        <td style="text-align:right; font-family:'JetBrains Mono',monospace; font-weight:700; color:#38bdf8;">${formatCurrency(item.total)}</td>
      `;
      tbody.append(tr);
    });
  });

  $('#table-grand-total').innerHTML = `<b>${formatCurrency(budget.grand_total)}</b>`;

  // Daily budget cards
  const dailyGrid = $('#daily-budget-cards');
  dailyGrid.innerHTML = '';
  (budget.daily_breakdown || []).forEach((d) => {
    const tile = document.createElement('div');
    tile.className = 'daily-tile-card';
    tile.innerHTML = `
      <div class="daily-day-label">Day ${d.day} Allocation</div>
      <div class="daily-day-amt">${formatCurrency(d.total)}</div>
      <div class="daily-day-items">${d.items.length} line items</div>
    `;
    dailyGrid.append(tile);
  });
}

function renderItineraryTimeline(days) {
  const timeline = $('#itinerary-timeline');
  timeline.innerHTML = '';
  if (!days.length) {
    timeline.innerHTML = '<div style="color:#64748b;font-size:12.5px;">No daily timeline generated.</div>';
    return;
  }
  days.forEach((d) => {
    const card = document.createElement('div');
    card.className = 'timeline-entry';
    card.innerHTML = `
      <h4>${d.title}</h4>
      <div class="timeline-period">
        <span class="timeline-period-badge">MORNING</span>
        <div>${d.morning}</div>
      </div>
      <div class="timeline-period">
        <span class="timeline-period-badge">AFTERNOON</span>
        <div>${d.afternoon}</div>
      </div>
      <div class="timeline-period">
        <span class="timeline-period-badge">EVENING</span>
        <div>${d.evening}</div>
      </div>
    `;
    timeline.append(card);
  });
}

function renderEvidenceSources(sources) {
  const evidenceList = $('#evidence-list');
  evidenceList.innerHTML = '';
  if (!sources.length) {
    evidenceList.innerHTML = '<div style="color:#64748b;font-size:12.5px;">No source references attached.</div>';
    return;
  }
  sources.forEach((s) => {
    const div = document.createElement('div');
    div.className = 'evidence-tile';
    div.innerHTML = `<div>✓ ${s}</div>`;
    evidenceList.append(div);
  });
}

// FORM SUBMISSION
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = query.value.trim();
  if (!text) {
    query.focus();
    return;
  }

  addChat('user', text);
  query.value = '';
  button.disabled = true;
  button.innerHTML = '<span>Orchestrating…</span>';

  try {
    const res = await fetch('/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        text,
        trip_id: currentTripId,
        detected_landmark: landmark,
      }),
    });

    if (!res.ok) throw new Error();
    const data = await res.json();
    addChat('assistant', data.answer);
    renderResponseData(data);
  } catch {
    addChat('assistant', 'I encountered an issue connecting to the travel orchestration engine. Please try again.');
  } finally {
    button.disabled = false;
    button.innerHTML = '<span>Plan Journey</span> <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
  }
});

// PDF EXPORT
async function handlePdfExport() {
  if (!latestPlanData) return;
  pdf.disabled = true;
  pdf.textContent = 'Generating PDF…';
  topbarPdf.disabled = true;
  topbarPdf.textContent = 'Generating…';

  try {
    const res = await fetch('/v1/plan/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: `${latestPlanData.trip_state?.destination || 'Travel'} Itinerary & Itemized Budget`,
        answer: latestPlanData.answer,
        context: latestPlanData.sources || [],
        budget: latestPlanData.budget,
      }),
    });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `TripPilot-${latestPlanData.trip_state?.destination || 'Plan'}-Budget.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    alert('Failed to generate PDF brief.');
  } finally {
    pdf.disabled = false;
    pdf.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg> Download PDF Itinerary';
    topbarPdf.disabled = false;
    topbarPdf.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg> Export PDF';
  }
}

pdf?.addEventListener('click', handlePdfExport);
topbarPdf?.addEventListener('click', handlePdfExport);

// RESET / NEW TRIP
$('#end-chat')?.addEventListener('click', async () => {
  try {
    await fetch(`/v1/memory/${userId}`, { method: 'DELETE' });
  } catch {}
  sessionStorage.removeItem('trippilotSessionId');
  conversation.innerHTML = '';
  card.hidden = true;
  welcome.hidden = false;
  topbarPdf.hidden = true;
  latestPlanData = null;
  currentTripId = null;
  query.value = '';
  $$('.scenario-item').forEach((o) => o.classList.remove('active'));
});

query.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') form.requestSubmit();
});
