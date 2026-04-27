// ═══════════════════════════════════════════════
//  Chunker — Smart narration splitting
//  Only splits at natural paragraph/story breaks
// ═══════════════════════════════════════════════

const CHUNK_MAX = 600;

export function chunkNarration(htmlText) {
  if (!htmlText) return [];

  // Strip HTML for length check
  const tmp = document.createElement('div');
  tmp.innerHTML = htmlText;
  const plain = (tmp.textContent || '').trim();

  // If short enough, don't split at all
  if (plain.length <= CHUNK_MAX) return [htmlText];

  // Split by double newlines (paragraph breaks in the narration HTML)
  // Also split on <br/><br/> or <br><br> patterns
  const normalized = htmlText.replace(/<br\s*\/?>\s*<br\s*\/?>/gi, '\n\n');
  const paragraphs = normalized.split(/\n\n+/).filter(p => p.trim());

  if (paragraphs.length <= 1) {
    // Single block — try splitting by sentences at natural pause points
    return splitBySentences(htmlText);
  }

  const chunks = [];
  let current = '';

  for (const para of paragraphs) {
    const paraPlain = para.replace(/<[^>]+>/g, '').trim();

    if (current.length === 0) {
      current = para;
      continue;
    }

    const combined = current + '\n\n' + para;

    if (combined.replace(/<[^>]+>/g, '').length > CHUNK_MAX && current.length > 0) {
      // Current chunk is ready — push it
      chunks.push(current.trim());
      current = para;
    } else {
      current = combined;
    }
  }

  if (current.trim()) chunks.push(current.trim());
  return chunks.length > 0 ? chunks : [htmlText];
}

function splitBySentences(html) {
  const plain = html.replace(/<[^>]+>/g, '').trim();
  if (plain.length <= CHUNK_MAX) return [html];

  // Split at sentence endings, but only at complete thoughts
  const sentences = html.match(/[^.!?\n]+[.!?]+\s*/g) || [html];
  const chunks = [];
  let current = '';

  for (const s of sentences) {
    const sPlain = s.replace(/<[^>]+>/g, '');
    if (current.length > 0 && (current + sPlain).length > CHUNK_MAX) {
      chunks.push(current.trim());
      current = s;
    } else {
      current += s;
    }
  }

  if (current.trim()) chunks.push(current.trim());
  return chunks.length > 0 ? chunks : [html];
}
