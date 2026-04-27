// ═══════════════════════════════════════════════
//  TTS — Browser SpeechSynthesis wrapper
// ═══════════════════════════════════════════════

let enabled = true;
let speaking = false;

function stripHTML(html) {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  tmp.querySelectorAll('script, style').forEach(el => el.remove());
  return (tmp.textContent || tmp.innerText || '').trim();
}

function splitChunks(text, maxLen = 200) {
  const sentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];
  const chunks = [];
  let current = '';
  for (const s of sentences) {
    if ((current + s).length > maxLen && current.length > 0) {
      chunks.push(current.trim());
      current = s;
    } else {
      current += s;
    }
  }
  if (current.trim()) chunks.push(current.trim());
  return chunks;
}

export function speak(htmlText) {
  if (!enabled) return;
  stop();
  const text = stripHTML(htmlText);
  if (!text || text.length < 5) return;
  const chunks = splitChunks(text, 200);
  let idx = 0;

  function next() {
    if (idx >= chunks.length) { speaking = false; return; }
    const u = new SpeechSynthesisUtterance(chunks[idx]);
    u.rate = 0.95;
    u.pitch = 0.9;
    u.volume = 0.8;
    const voices = speechSynthesis.getVoices();
    const pref = voices.find(v =>
      v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Daniel'))
    );
    if (pref) u.voice = pref;
    u.onend = () => { idx++; next(); };
    u.onerror = () => { speaking = false; };
    speaking = true;
    speechSynthesis.speak(u);
  }
  next();
}

export function stop() {
  speechSynthesis.cancel();
  speaking = false;
}

export function toggle() {
  enabled = !enabled;
  if (!enabled) stop();
  return enabled;
}

export function isEnabled() { return enabled; }
export function isSpeaking() { return speaking; }

// Preload voices
if (typeof speechSynthesis !== 'undefined') {
  speechSynthesis.getVoices();
  speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
}
