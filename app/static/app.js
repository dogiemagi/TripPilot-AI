const form = document.querySelector('#query-form');
const query = document.querySelector('#query');
const card = document.querySelector('#result-card');
const welcome = document.querySelector('#welcome');
const button = document.querySelector('#analyze');
const upload = document.querySelector('#file-input');
let landmark = null;

document.querySelectorAll('.scenario').forEach((item) => item.addEventListener('click', () => {
  document.querySelectorAll('.scenario').forEach((other) => other.classList.remove('active'));
  item.classList.add('active'); query.value = item.dataset.query; query.focus();
}));

upload.addEventListener('change', async () => {
  const file = upload.files[0]; if (!file) return;
  const modality = file.type.startsWith('image/') ? 'image' : file.type.startsWith('audio/') ? 'audio' : file.type.startsWith('video/') ? 'video' : null;
  const status = document.querySelector('#upload-status');
  if (!modality) { status.textContent = 'Please choose an image, audio, or video file.'; return; }
  status.textContent = `Processing ${file.name}…`;
  const body = new FormData(); body.append('file', file);
  try { const response = await fetch(`/v1/multimodal/${modality}`, { method: 'POST', body }); if (!response.ok) throw new Error(); const data = await response.json(); landmark = modality === 'image' ? 'uploaded travel image' : null; status.textContent = `✓ ${data.filename} attached · ${modality}`; }
  catch { status.textContent = 'Could not process this file. Please try another file.'; }
});

form.addEventListener('submit', async (event) => {
  event.preventDefault(); const text = query.value.trim(); if (!text) { query.focus(); return; }
  button.disabled = true; button.textContent = 'Thinking…';
  try {
    const response = await fetch('/v1/travel/query', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:'web-traveler',text,detected_landmark:landmark})});
    if (!response.ok) throw new Error(); const data = await response.json();
    welcome.hidden = true; card.hidden = false;
    document.querySelector('#answer').textContent = data.answer;
    document.querySelector('#result-title').textContent = data.intent.replaceAll('_',' ');
    document.querySelector('#intent-badge').textContent = `✦ INTENT: ${data.intent.replaceAll('_',' ').toUpperCase()}`;
    document.querySelector('#confidence-badge').textContent = `● ${Math.round(data.confidence * 100)}% confidence`;
    const evidence = document.querySelector('#evidence-list'); evidence.innerHTML = '';
    (data.retrieved_context.length ? data.retrieved_context : [{topic:'Travel guidance',content:'Tailor this plan with dates, budget, and travel style.'}]).forEach((item) => { const li = document.createElement('li'); li.textContent = `${item.topic} — ${item.content}`; evidence.appendChild(li); });
  } catch { alert('TripPilot could not reach the service. Please try again.'); }
  finally { button.disabled = false; button.innerHTML = 'Plan trip <span>→</span>'; }
});

query.addEventListener('keydown', (event) => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') form.requestSubmit(); });
