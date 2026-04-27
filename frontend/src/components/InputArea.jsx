import { useState, useRef, useEffect } from 'react';

const MAX_CHARS = 200;

export default function InputArea({ onSubmit, disabled }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);

  const handleSubmit = () => {
    const val = text.trim();
    if (!val || disabled) return;
    onSubmit(val);
    setText('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit();
  };

  const len = text.length;
  const countClass = len > MAX_CHARS ? 'over' : len > MAX_CHARS * 0.8 ? 'warn' : '';

  useEffect(() => {
    inputRef.current?.focus();
  }, [disabled]);

  return (
    <div className="input-area">
      <input type="text" ref={inputRef} placeholder="What do you do?" autoComplete="off"
        maxLength={MAX_CHARS} value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled} />
      <span className={`char-count ${countClass}`}>{len}/{MAX_CHARS}</span>
      <button onClick={handleSubmit} disabled={disabled || !text.trim()}>Act</button>
    </div>
  );
}
