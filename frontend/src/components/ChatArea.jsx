import { useEffect, useRef } from 'react';

export default function ChatArea({ messages, onChoiceClick }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [messages]);

  return (
    <div className="chat-area" ref={ref}>
      {messages.map(msg => (
        <div key={msg.id} className={`msg ${msg.type}`}>
          <span dangerouslySetInnerHTML={{ __html: msg.content }} />
          {/* Wire up choice buttons */}
          {msg.type === 'system' && msg.content.includes('choice-btn') && (
            <ChoiceBinder content={msg.content} onChoice={onChoiceClick} />
          )}
        </div>
      ))}
    </div>
  );
}

// This component handles click delegation for dynamically rendered choice buttons
function ChoiceBinder({ content, onChoice }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el) return;
    const handler = (e) => {
      const btn = e.target.closest('.choice-btn');
      if (btn) {
        e.stopPropagation();
        const choice = btn.getAttribute('data-choice') || btn.textContent;
        onChoice(choice);
      }
    };
    el.addEventListener('click', handler);
    return () => el.removeEventListener('click', handler);
  }, [content, onChoice]);
  return <span ref={ref} style={{ display: 'none' }} />;
}
