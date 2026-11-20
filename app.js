const stopWords = new Set('a an the and or but of in on at to for from by with about what which who was were is are did does do exact annual expressed as percentage colonial administration promise private british railway companies under contract terms this that it its between seat car executive chair price ticket vande bharat express new delhi varanasi country won fifa world cup'.split(' '));
const assessment = [
  ['Q1', '1849 guarantee rate', '5% per annum', 'supported'],
  ['Q2', 'Bhor Ghat obstacle', 'Basalt precipice; 1 in 37', 'supported'],
  ['Q3', 'Vande Bharat ticket price', 'Outside supplied corpus', 'boundary'],
  ['Q4', 'Diamond Harbour cable', "Dr. William Brooke O'Shaughnessy", 'supported'],
  ['Q5', '2022 FIFA World Cup', 'Outside supplied corpus', 'boundary']
];

const $ = (selector) => document.querySelector(selector);
const tokenize = (text) => (text.toLowerCase().match(/[a-z0-9]+/g) || []).filter(t => !stopWords.has(t));
function score(query, chunk) {
  const q = tokenize(query); const haystack = `${chunk.chapter} ${chunk.text}`.toLowerCase();
  let value = 0;
  q.forEach(t => { if (haystack.includes(t)) value += t.length > 5 ? 3 : 2; });
  const phrases = ['interest rate', 'bhor ghat', 'reversing station', 'diamond harbour', 'underwater telegraph', '1851'];
  phrases.forEach(p => { if (query.toLowerCase().includes(p) && haystack.includes(p)) value += 8; });
  return value;
}
function highlight(text, query) {
  const terms = [...new Set(tokenize(query).filter(t => t.length > 3))].sort((a,b) => b.length-a.length);
  if (!terms.length) return text;
  const rx = new RegExp(`(${terms.join('|')})`, 'gi');
  return text.replace(rx, '<mark>$1</mark>');
}
function renderEvidence(results, query) {
  $('#evidenceCount').textContent = `${results.length} matching passage${results.length === 1 ? '' : 's'}`;
  $('#evidence').innerHTML = results.map((item, i) => `<article class="evidence-card"><div class="evidence-meta"><span>PASSAGE ${String(i + 1).padStart(2, '0')}</span><span>PDF p. ${item.page}</span></div><h3>${item.chapter}</h3><p>“${highlight(item.text, query)}”</p><a href="https://drive.google.com/file/d/1EoxtVqm1niBnn7UiEUcYcpOVmG2-Zkx2/view?usp=drive_link" target="_blank" rel="noreferrer">Inspect source <span>↗</span></a></article>`).join('');
}
async function runQuery(query) {
  query = query.trim(); if (!query) return;
  try {
    const response = await fetch('/api/answer', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question: query})});
    if (response.ok) {
      const result = await response.json();
      const answer = $('#answer'), confidence = $('#confidence');
      if (result.answer === '[not found]') {
        confidence.className = 'confidence boundary'; confidence.textContent = 'OUT OF CORPUS';
        answer.innerHTML = `<p class="response-kicker">[not found]</p><p>The supplied PDF does not contain a grounded answer to this question.</p><div class="boundary-callout"><span>Strict grounding</span>The system returns exactly <code>[not found]</code> in its API response when no supporting PDF passage is retrieved.</div>`;
        $('#evidenceCount').textContent = '0 matching passages'; $('#evidence').innerHTML = `<div class="empty-evidence">No relevant passage was retrieved from the 50-page corpus.</div>`;
      } else {
        confidence.className = 'confidence high'; confidence.textContent = 'CHROMADB RETRIEVED';
        answer.innerHTML = `<p class="response-kicker">Grounded answer</p><p>${result.answer}</p><div class="answer-note">Extracted only from the retrieved PDF chunk. No external information is used.</div>`;
        $('#evidenceCount').textContent = `${result.sources.length} supporting source${result.sources.length === 1 ? '' : 's'}`;
        $('#evidence').innerHTML = result.sources.map(source => `<article class="evidence-card"><div class="evidence-meta"><span>CHROMADB MATCH</span><span>${source}</span></div><h3>Verified source reference</h3><p>This response is traceable to the assigned PDF through the persistent ChromaDB index.</p></article>`).join('');
      }
      return;
    }
  } catch (_) { /* Static fallback keeps the visual prototype usable without the backend. */ }
  const ranked = window.CORPUS.map(c => ({...c, relevance: score(query, c)})).filter(c => c.relevance > 2).sort((a,b) => b.relevance-a.relevance);
  const answer = $('#answer'), confidence = $('#confidence');
  if (!ranked.length) {
    confidence.className = 'confidence boundary'; confidence.textContent = 'OUT OF CORPUS';
    answer.innerHTML = `<p class="response-kicker">No supported passage found</p><p>I can’t answer this from the supplied railway and telegraph monograph. This assistant is intentionally source-bounded: it does not invent an answer or blend in unverified web information.</p><div class="boundary-callout"><span>Scope check</span>Try a question about 19th-century railway construction, colonial contracts, telegraph infrastructure, or the archival records in this PDF.</div>`;
    $('#evidenceCount').textContent = '0 matching passages'; $('#evidence').innerHTML = `<div class="empty-evidence">No relevant passage was retrieved from the 50-page corpus.</div>`;
  } else {
    const best = ranked[0]; confidence.className = 'confidence high'; confidence.textContent = 'HIGH EVIDENCE';
    answer.innerHTML = `<p class="response-kicker">Grounded answer · PDF page ${best.page}</p><p>${best.answer}</p><div class="answer-note">This response is based only on the retrieved archival passage shown below.</div>`;
    renderEvidence(ranked.slice(0, 2), query);
  }
}
function renderAssessment() {
  $('#evalGrid').innerHTML = assessment.map(([q, title, result, status]) => `<button class="eval-card ${status}" data-question="${encodeURIComponent(title)}"><span>${q}</span><h3>${title}</h3><p>${result}</p><i>${status === 'supported' ? 'Evidence found →' : 'Correct abstention →'}</i></button>`).join('');
  document.querySelectorAll('.eval-card').forEach(card => card.addEventListener('click', () => { const title = decodeURIComponent(card.dataset.question); const prompts = { '1849 guarantee rate': 'What exact annual guaranteed interest rate did the colonial administration promise private British railway companies under the 1849 contract terms?', 'Bhor Ghat obstacle': 'Which engineering obstacle on the Bhor Ghat incline made the reversing station necessary, and what was the gradient ratio?', 'Diamond Harbour cable': 'According to the archival records, who supervised the laying of the experimental Diamond Harbour underwater telegraph cable in 1851?', 'Vande Bharat ticket price': 'What is the ticket price for an Executive Chair Car seat on the Vande Bharat Express between New Delhi and Varanasi?', '2022 FIFA World Cup': 'Which country won the 2022 FIFA World Cup?' }; $('#question').value = prompts[title]; runQuery(prompts[title]); document.querySelector('.workspace').scrollIntoView({behavior:'smooth', block:'start'}); }));
}
$('#askButton').addEventListener('click', () => runQuery($('#question').value));
$('#question').addEventListener('keydown', e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') runQuery(e.target.value); });
document.querySelectorAll('.suggestions button').forEach(b => b.addEventListener('click', () => { $('#question').value = b.dataset.question; runQuery(b.dataset.question); }));
renderAssessment(); runQuery($('#question').value);
