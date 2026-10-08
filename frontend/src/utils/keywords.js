// Adventure keywords are edited as a list of chips and sent as one string
// (the server caps the string at 200 characters).

export const MAX_KEYWORDS = 10;
export const MAX_KEYWORD_LENGTH = 40;
export const MAX_KEYWORDS_TEXT = 200;

export function normalizeKeyword(raw) {
  return String(raw || '').replace(/\s+/g, ' ').trim().slice(0, MAX_KEYWORD_LENGTH);
}

// Split pasted or typed text like "haunted castle, undead; siege" into keywords.
export function splitKeywords(text) {
  return String(text || '').split(/[,;\n]+/).map(normalizeKeyword).filter(Boolean);
}

export function keywordsToText(list) {
  return list.join(', ');
}

// Add keywords, skipping duplicates (case-insensitive) and anything past the limits.
export function addKeywords(list, incoming) {
  const result = [...list];
  for (const keyword of incoming.map(normalizeKeyword).filter(Boolean)) {
    if (result.length >= MAX_KEYWORDS) break;
    if (result.some(k => k.toLowerCase() === keyword.toLowerCase())) continue;
    if (keywordsToText([...result, keyword]).length > MAX_KEYWORDS_TEXT) break;
    result.push(keyword);
  }
  return result;
}
