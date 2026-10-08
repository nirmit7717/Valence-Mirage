import { useRef, useState } from 'react';
import { MAX_KEYWORDS, addKeywords, splitKeywords } from '../utils/keywords';

const SUGGESTIONS = ['haunted castle', 'cyberpunk city', 'undead siege', 'heist', 'ancient ruins', 'dragon hunt', 'political intrigue', 'post-apocalyptic wasteland'];

// Keywords as removable chips: Enter or comma adds, Backspace on an empty box removes the last.
export default function KeywordInput({ keywords, onChange }) {
  const [draft, setDraft] = useState('');
  const inputRef = useRef(null);
  const full = keywords.length >= MAX_KEYWORDS;

  const commit = (text) => {
    const pieces = splitKeywords(text);
    if (pieces.length) onChange(addKeywords(keywords, pieces));
    setDraft('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',' || e.key === 'Tab') {
      if (!draft.trim()) return; // let Tab move focus normally when there's nothing to add
      e.preventDefault();
      commit(draft);
    } else if (e.key === 'Backspace' && !draft && keywords.length) {
      onChange(keywords.slice(0, -1));
    }
  };

  const onInput = (value) => {
    // Pasting "a, b, c" (or typing a separator) turns everything before it into chips.
    if (/[,;\n]/.test(value)) {
      const parts = value.split(/[,;\n]/);
      const rest = parts.pop();
      commit(parts.join(','));
      setDraft(rest);
    } else {
      setDraft(value);
    }
  };

  const remove = (index) => {
    onChange(keywords.filter((_, i) => i !== index));
    inputRef.current?.focus();
  };

  const unused = SUGGESTIONS.filter(s => !keywords.some(k => k.toLowerCase() === s));

  return (
    <div className="keyword-editor">
      <div className="keyword-field" onClick={() => inputRef.current?.focus()}>
        {keywords.map((keyword, i) => (
          <span key={keyword} className="keyword-chip">
            {keyword}
            <button type="button" className="keyword-chip-remove" aria-label={`Remove ${keyword}`}
              onClick={(e) => { e.stopPropagation(); remove(i); }}>
              ✕
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          className="keyword-input"
          value={draft}
          disabled={full}
          maxLength={60}
          placeholder={full ? 'Keyword limit reached' : keywords.length ? 'Add another…' : 'Add adventure keywords (e.g. haunted castle)…'}
          aria-label="Add an adventure keyword"
          onChange={(e) => onInput(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => draft.trim() && commit(draft)}
        />
      </div>
      <div className="keyword-hint">Press Enter or comma to add · {keywords.length}/{MAX_KEYWORDS}</div>
      {!full && unused.length > 0 && (
        <div className="keyword-suggestions" aria-label="Suggested keywords">
          {unused.slice(0, 5).map(s => (
            <button key={s} type="button" className="keyword-suggestion" onClick={() => onChange(addKeywords(keywords, [s]))}>
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
