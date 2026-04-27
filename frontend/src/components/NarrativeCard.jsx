import { useState, useEffect, useCallback } from 'react';
import { useTypewriter } from '../utils/typewriter';
import { chunkNarration } from '../utils/chunker';
import * as tts from '../utils/tts';

export default function NarrativeCard({ narration, onChoice, onDismiss, animationsEnabled, textSpeed, inputDisabled }) {
  const [phase, setPhase] = useState('hidden'); // hidden | fading-in | visible | fading-out
  const [displayedText, setDisplayedText] = useState('');
  const [chunkIndex, setChunkIndex] = useState(0);
  const [chunks, setChunks] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [customText, setCustomText] = useState('');
  const fadeTimerRef = useCallback((t) => { return t; }, []);

  const { typewriterRender, skip, cancel } = useTypewriter(textSpeed || 20);
  const timerRef = useState(null);
  const setTimer = (t) => { if (timerRef[0]) clearTimeout(timerRef[0]); timerRef[1](t); };

  useEffect(() => {
    if (!narration) {
      if (phase !== 'hidden') {
        setPhase('fading-out');
        const t = setTimeout(() => setPhase('hidden'), 500);
        setTimer(t);
      }
      return;
    }

    if (phase === 'visible' || phase === 'fading-in') {
      setPhase('fading-out');
      const t = setTimeout(() => startNew(narration), 450);
      setTimer(t);
      return;
    }

    startNew(narration);
  }, [narration]);

  useEffect(() => {
    return () => { if (timerRef[0]) clearTimeout(timerRef[0]); };
  }, []);

  function startNew(narr) {
    const parsed = chunkNarration(narr.html);
    setChunks(parsed);
    setChunkIndex(0);
    setShowActions(false);
    setCustomText('');

    setPhase('fading-in');
    setTimeout(() => setPhase('visible'), 50);

    tts.speak(narr.html);

    if (parsed.length > 0 && animationsEnabled) {
      setIsTyping(true);
      typewriterRender(parsed[0], setDisplayedText, () => setIsTyping(false));
    } else {
      setDisplayedText(parsed[0] || narr.html);
    }
  }

  const handleBodyClick = useCallback(() => {
    if (isTyping) skip();
  }, [isTyping, skip]);

  const handleContinue = useCallback(() => {
    tts.stop();
    cancel();

    const nextIdx = chunkIndex + 1;
    if (nextIdx < chunks.length) {
      setChunkIndex(nextIdx);
      if (animationsEnabled) {
        setIsTyping(true);
        typewriterRender(chunks[nextIdx], setDisplayedText, () => setIsTyping(false));
      } else {
        setDisplayedText(chunks[nextIdx]);
      }
      tts.speak(chunks[nextIdx]);
    } else {
      if (narration?.choices?.length > 0) {
        setShowActions(true);
      } else {
        onDismiss?.();
      }
    }
  }, [chunkIndex, chunks, narration, animationsEnabled, typewriterRender, cancel, onDismiss]);

  const handleChoice = useCallback((choice) => {
    tts.stop();
    cancel();
    onChoice(choice);
  }, [onChoice, cancel]);

  const handleCustomSubmit = useCallback(() => {
    const text = customText.trim();
    if (!text) return;
    tts.stop();
    cancel();
    onChoice(text);
  }, [customText, onChoice, cancel]);

  if (phase === 'hidden') return null;

  const isLastChunk = chunkIndex >= chunks.length - 1;
  const showChoices = isLastChunk && showActions;

  return (
    <div className={`nc-overlay ${phase === 'fading-in' ? 'nc-fade-enter' : phase === 'fading-out' ? 'nc-fade-exit' : 'nc-fade-active'}`}>
      <div className={`nc-card ${phase === 'fading-in' ? 'nc-card-enter' : phase === 'fading-out' ? 'nc-card-exit' : 'nc-card-active'}`}
        onClick={handleBodyClick}>

        {/* Ornate top border */}
        <div className="nc-ornament">⸻ ✦ ⸻</div>

        {/* Body */}
        <div className="nc-body">
          <div className="nc-text" dangerouslySetInnerHTML={{ __html: displayedText }} />
          {narration?.meta && (
            <div className="nc-meta" dangerouslySetInnerHTML={{ __html: narration.meta }} />
          )}
          {chunks.length > 1 && (
            <div className="nc-chunk-ind">— {chunkIndex + 1} / {chunks.length} —</div>
          )}
        </div>

        {/* Actions */}
        <div className="nc-actions">
          {showChoices && narration?.choices?.map((c, i) => (
            <button key={i} className="nc-choice-btn" onClick={(e) => { e.stopPropagation(); handleChoice(c); }} disabled={inputDisabled}>
              {c}
            </button>
          ))}

          {showChoices && !inputDisabled && (
            <div className="nc-custom-action" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                placeholder="Write your own action..."
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleCustomSubmit(); }}
                maxLength={200}
              />
              <button className="nc-custom-submit" onClick={handleCustomSubmit} disabled={!customText.trim()}>
                ▸
              </button>
            </div>
          )}

          {!showChoices && (
            <button className="nc-continue-btn" onClick={(e) => { e.stopPropagation(); handleContinue(); }}>
              {isLastChunk && narration?.choices?.length ? 'See Options ▸' : 'Continue ▸'}
            </button>
          )}
        </div>

        {/* TTS toggle — bottom corner */}
        <button className={`nc-tts-btn ${tts.isEnabled() ? 'active' : ''}`}
          onClick={(e) => { e.stopPropagation(); const on = tts.toggle(); e.currentTarget.textContent = on ? '🔊' : '🔇'; e.currentTarget.classList.toggle('active', on); }}>
          {tts.isEnabled() ? '🔊' : '🔇'}
        </button>

        {/* Ornate bottom border */}
        <div className="nc-ornament">⸻ ✦ ⸻</div>
      </div>
    </div>
  );
}
