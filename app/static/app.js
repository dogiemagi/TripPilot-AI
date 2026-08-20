const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const form = $('#query-form');
const query = $('#query');
const card = $('#result-card');
const welcome = $('#welcome');
const button = $('#analyze');
const upload = $('#file-input');
const mic = $('#mic-button');
const attachment = $('#attachment-button');
const conversation = $('#conversation');
const pdf = $('#download-pdf');

let landmark = null;
let currentTripId = null;
let latestPlanData = null;

const userId = sessionStorage.trippilotSessionId || (sessionStorage.trippilotSessionId = crypto.randomUUID());

function formatCurrency(val) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
}

function addChat(who, text) {
  const item = document.createElement('div');
  item.className = `chat ${who}`;
  item.innerHTML = `<small>${who === 'user' ? 'YOU' : 'TRIPPILOT AI COPILOT'}</small>`;
  item.append(document.createTextNode(text));
  conversation.append(item);
  item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// TAB SWITCHING
$$('.rtab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $$('.rtab').forEach((t) => t.classList.remove('active'));
    $$('.tab-pane').forEach((p) => p.classList.remove('active'));
    tab.classList.add('active');
    const target = $(`#pane-${tab.dataset.tab}`);
    if (target) target.classList.add('active');
  });
});

// QUICK CHIPS & SCENARIO BUTTONS
$$('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    query.value = chip.dataset.action;
    form.requestSubmit();
  });
});

$$('.scenario').forEach((item) => {
  item.addEventListener('click', () => {
    $$('.scenario').forEach((o) => o.classList.remove('active'));
    item.classList.add('active');
    query.value = item.dataset.query;
    form.requestSubmit();
  });
});

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
  status.textContent = `Processing ${file.name}…`;

  const body = new FormData();
  body.append('file', file);

  try {
    const res = await fetch(`/v1/multimodal/${type}`, { method: 'POST', body });
    if (!res.ok) throw new Error();
    const data = await res.json();
    landmark = data.detected_landmark || file.name;
    status.textContent = `✓ Attached: ${data.detected_landmark || file.name}`;
    if (data.extracted_prompt) {
      query.value = data.extracted_prompt;
      query.focus();
    }
  } catch {
    status.textContent = 'Could not process media. Please try again.';
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
  mic.textContent = '■';

  rec.onresult = (e) => {
    query.value = Array.from(e.results).map((r) => r[0].transcript).join('');
  };
  rec.onend = () => {
    mic.classList.remove('recording');
    mic.textContent = '◉';
    if (query.value.trim()) form.requestSubmit();
  };
  rec.start();
});

// RENDER RESPONSE DATA
function renderResponseData(data) {
  latestPlanData = data;
  currentTripId = data.trip_id;

  welcome.hidden = true;
  card.hidden = false;

  // Badges
  $('#intent-badge').textContent = `✦ INTENT: ${data.intent.replaceAll('_', ' ').toUpperCase()}`;
  $('#model-badge').textContent = `◈ ${data.model_used.toUpperCase()}`;
  $('#confidence-badge').textContent = `● ${Math.round(data.confidence * 100)}% CONFIDENCE`;

  // Answer
  $('#answer').textContent = data.answer;

  // Render Over-Budget Warning if applicable
  const bAlert = $('#budget-alert');
  if (data.budget && data.budget.is_over_budget) {
    bAlert.hidden = false;
    $('#overage-tag').textContent = `${formatCurrency(data.budget.overage_amount)} over`;
    const redList = $('#reduction-list');
    redList.innerHTML = '<b>Cost Reduction Recommendations:</b>';
    (data.budget.reduction_suggestions || []).forEach((s, idx) => {
      const div = document.createElement('div');
      div.className = 'reduction-item';
      div.innerHTML = `${idx + 1}. <b>${s.action}</b> → <span style="color:#34d399;">Save ${formatCurrency(s.estimated_saving)}</span> (${s.description})`;
      redList.append(div);
    });
  } else {
    bAlert.hidden = true;
  }

  // Render Cards (Flight, Hotel, Activities)
  renderFlightCards(data.flight_recommendations || []);
  renderHotelCards(data.hotel_recommendations || []);
  renderActivityCards(data.activity_recommendations || []);

  // Render Itemized Budget
  if (data.budget) {
    renderBudgetTable(data.budget);
  }

  // Render Itinerary Timeline
  renderItineraryTimeline(data.itinerary_days || []);

  // Render Evidence / RAG
  const evidenceList = $('#evidence-list');
  evidenceList.innerHTML = '';
  (data.sources || []).forEach((s) => {
    const li = document.createElement('li');
    li.textContent = s;
    evidenceList.append(li);
  });

  pdf.hidden = !data.ready_to_download;
}

function renderFlightCards(flights) {
  const container = $('#flight-cards');
  container.innerHTML = '';
  flights.forEach((f) => {
    const card = document.createElement('div');
    card.className = 'travel-card';
    card.innerHTML = `
      <div class="tc-header">
        <div class="tc-title">${f.airline} ${f.flight_number}</div>
        <span class="tc-score">${f.score}% Score</span>
      </div>
      <div class="tc-detail">${f.origin} → ${f.destination} · ${f.departure_time} - ${f.arrival_time} (${f.duration})</div>
      <div class="tc-reason">💡 ${f.recommendation_reason}</div>
      <div class="tc-footer">
        <div class="tc-price">${formatCurrency(f.price.amount)}</div>
        <button class="tc-btn" data-type="flight" data-id="${f.id}">Select Flight</button>
      </div>
    `;
    container.append(card);
  });
}

function renderHotelCards(hotels) {
  const container = $('#hotel-cards');
  container.innerHTML = '';
  hotels.forEach((h) => {
    const card = document.createElement('div');
    card.className = 'travel-card';
    card.innerHTML = `
      <div class="tc-header">
        <div class="tc-title">${h.name}</div>
        <span class="tc-score">${h.user_rating}/10 ★</span>
      </div>
      <div class="tc-detail">${h.neighborhood}, ${h.city} · ${h.star_rating}★ (${h.cancellation_policy})</div>
      <div class="tc-reason">💡 ${h.recommendation_reason}</div>
      <div class="tc-footer">
        <div class="tc-price">${formatCurrency(h.price_per_night.amount)}/night</div>
        <button class="tc-btn" data-type="hotel" data-id="${h.id}">Select Hotel</button>
      </div>
    `;
    container.append(card);
  });
}

function renderActivityCards(activities) {
  const container = $('#activity-cards');
  container.innerHTML = '';
  activities.forEach((a) => {
    const card = document.createElement('div');
    card.className = 'travel-card';
    card.innerHTML = `
      <div class="tc-header">
        <div class="tc-title">${a.name}</div>
        <span class="tc-score">${a.rating} ★</span>
      </div>
      <div class="tc-detail">${a.category} · Timing: ${a.best_time} · Crowd: ${a.crowd_level}</div>
      <div class="tc-reason">💡 ${a.recommendation_reason}</div>
      <div class="tc-footer">
        <div class="tc-price">${formatCurrency(a.price.amount)}</div>
        <button class="tc-btn" data-type="activity" data-id="${a.id}">Add to Trip</button>
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
  if (budget.remaining_budget !== null) {
    remEl.textContent = formatCurrency(budget.remaining_budget);
    remEl.className = budget.is_over_budget ? '' : 'positive';
    remEl.style.color = budget.is_over_budget ? '#ef4444' : '#34d399';
  } else {
    remEl.textContent = 'N/A';
  }

  budget.categories.forEach((cat) => {
    cat.items.forEach((item, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${idx === 0 ? `<b>${cat.category.replace('_', ' ').toUpperCase()}</b>` : ''}</td>
        <td>${item.name} ${item.notes ? `<small style="color:#94a3b8;display:block;">${item.notes}</small>` : ''}</td>
        <td>${item.quantity}</td>
        <td>${formatCurrency(item.unit_price)}</td>
        <td><b>${formatCurrency(item.total)}</b></td>
      `;
      tbody.append(tr);
    });
  });

  $('#table-grand-total').innerHTML = `<b>${formatCurrency(budget.grand_total)}</b>`;

  // Daily budget cards
  const dailyGrid = $('#daily-budget-cards');
  dailyGrid.innerHTML = '';
  (budget.daily_breakdown || []).forEach((d) => {
    const card = document.createElement('div');
    card.className = 'daily-card';
    card.innerHTML = `
      <b>Day ${d.day} Allocation</b>
      <span>${formatCurrency(d.total)}</span>
      <small style="color:#94a3b8;font-size:11px;">${d.items.length} line items</small>
    `;
    dailyGrid.append(card);
  });
}

function renderItineraryTimeline(days) {
  const timeline = $('#itinerary-timeline');
  timeline.innerHTML = '';
  days.forEach((d) => {
    const div = document.createElement('div');
    div.className = 'timeline-day';
    div.innerHTML = `
      <h4>${d.title}</h4>
      <div class="day-leg"><b>Morning:</b> ${d.morning}</div>
      <div class="day-leg"><b>Afternoon:</b> ${d.afternoon}</div>
      <div class="day-leg"><b>Evening:</b> ${d.evening}</div>
    `;
    timeline.append(div);
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
  button.textContent = 'Orchestrating…';

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
    button.innerHTML = 'Plan Trip <span>→</span>';
  }
});

// PDF EXPORT
pdf.addEventListener('click', async () => {
  if (!latestPlanData) return;
  pdf.disabled = true;
  pdf.textContent = 'Generating PDF…';
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
    pdf.textContent = '⇩ Download Official PDF Itinerary & Budget';
  }
});

// RESET SESSION
$('#end-chat').addEventListener('click', async () => {
  try {
    await fetch(`/v1/memory/${userId}`, { method: 'DELETE' });
  } catch {}
  sessionStorage.removeItem('trippilotSessionId');
  conversation.innerHTML = '';
  card.hidden = true;
  welcome.hidden = false;
  latestPlanData = null;
  currentTripId = null;
  query.value = '';
});

query.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') form.requestSubmit();
});
