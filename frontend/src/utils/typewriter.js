// ═══════════════════════════════════════════════
//  Typewriter — character-by-character reveal
// ═══════════════════════════════════════════════

import { useRef, useCallback } from 'react';

const DEFAULT_SPEED = 20; // ms per character
const SKIP_THRESHOLD = 800; // chars — skip animation if longer

export function useTypewriter(speed = DEFAULT_SPEED) {
  const timerRef = useRef(null);
  const skipRef = useRef(false);

  const cancel = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const typewriterRender = useCallback((text, setDisplayed, onComplete) => {
    cancel();
    skipRef.current = false;

    // Skip if very long
    if (text.length > SKIP_THRESHOLD) {
      setDisplayed(text);
      onComplete?.();
      return;
    }

    let idx = 0;
    setDisplayed('');

    timerRef.current = setInterval(() => {
      if (skipRef.current || idx >= text.length) {
        clearInterval(timerRef.current);
        timerRef.current = null;
        setDisplayed(text);
        onComplete?.();
        return;
      }
      // Reveal a few chars at a time for speed
      const chunk = Math.min(2, text.length - idx);
      idx += chunk;
      setDisplayed(text.slice(0, idx));
    }, speed);
  }, [speed, cancel]);

  const skip = useCallback(() => {
    skipRef.current = true;
  }, []);

  return { typewriterRender, skip, cancel };
}
