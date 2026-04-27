import { useState } from 'react';
import * as tts from '../utils/tts';

export default function SettingsPanel({ animationsEnabled, setAnimationsEnabled, textSpeed, setTextSpeed }) {
  const [open, setOpen] = useState(false);
  const [ttsOn, setTtsOn] = useState(tts.isEnabled());

  const toggleTts = () => {
    const on = tts.toggle();
    setTtsOn(on);
  };

  return (
    <>
      <button className="settings-toggle" onClick={() => setOpen(!open)} title="Settings">
        ⚙️
      </button>
      {open && (
        <div className="settings-panel">
          <div className="settings-title">⚙️ Settings</div>
          <label className="settings-row">
            <span>🔊 TTS</span>
            <input type="checkbox" checked={ttsOn} onChange={toggleTts} />
          </label>
          <label className="settings-row">
            <span>✨ Animations</span>
            <input type="checkbox" checked={animationsEnabled} onChange={() => setAnimationsEnabled(!animationsEnabled)} />
          </label>
          <label className="settings-row">
            <span>⌨️ Text Speed</span>
            <input type="range" min="5" max="50" value={textSpeed} onChange={e => setTextSpeed(parseInt(e.target.value))} />
            <span className="speed-label">{textSpeed}ms</span>
          </label>
        </div>
      )}
    </>
  );
}
