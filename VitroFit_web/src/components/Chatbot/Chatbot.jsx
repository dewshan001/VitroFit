import { useState, useRef, useEffect, useCallback } from 'react';
import './Chatbot.css';

/* ─────────────────────────────────────────
   ICONS
───────────────────────────────────────── */
const IconBot = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    <line x1="12" y1="3" x2="12" y2="7"/>
    <circle cx="9" cy="16" r="1" fill="currentColor"/>
    <circle cx="15" cy="16" r="1" fill="currentColor"/>
  </svg>
);

const IconSend = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);

const IconClose = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const IconChevron = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="18 15 12 9 6 15"/>
  </svg>
);

const IconClear = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
  </svg>
);

const CHATBOT_API = import.meta.env.VITE_CHATBOT_API_URL || 'http://localhost:8000/api/chat';

const WELCOME_MSG = {
  id: 'welcome',
  role: 'bot',
  text: "Hey there! 💪 I'm **VitroBot**, your personal AI fitness assistant.\n\nAsk me anything about workouts, personalized diets, gym locations, or your VitroFit membership!",
  ts: Date.now(),
};

const QUICK_PROMPTS = [
  'Best exercises for beginners?',
  'Suggest a 4-day workout split',
  'High-protein nutrition tips',
  'How do I find a gym near me?',
];

/* ─────────────────────────────────────────
   TYPING INDICATOR
───────────────────────────────────────── */
function TypingDots() {
  return (
    <div className="vb-typing">
      <div className="vb-typing-avatar">
        <IconBot />
      </div>
      <div className="vb-typing-bubble">
        <span className="vb-dot" />
        <span className="vb-dot" />
        <span className="vb-dot" />
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────
   MESSAGE BUBBLE
───────────────────────────────────────── */
function MessageBubble({ msg, isNew }) {
  const isBot = msg.role === 'bot';

  // Enhanced markdown formatter: bold, italic, code, lists, line breaks
  const formatText = (text) => {
    if (!text) return '';
    let formatted = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks ```code```
    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre class="vb-code-block"><code>$1</code></pre>');

    // Inline code `code`
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="vb-inline-code">$1</code>');

    // Bold **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // List items starting with '-' or '•'
    formatted = formatted.replace(/^[•\-]\s+(.*)$/gm, '<li class="vb-list-item">$1</li>');
    formatted = formatted.replace(/((?:<li class="vb-list-item">.*<\/li>\s*)+)/g, '<ul class="vb-list">$1</ul>');

    // Numbered lists '1. item'
    formatted = formatted.replace(/^\d+\.\s+(.*)$/gm, '<li class="vb-num-item">$1</li>');
    formatted = formatted.replace(/((?:<li class="vb-num-item">.*<\/li>\s*)+)/g, '<ol class="vb-ol">$1</ol>');

    // Convert newlines not already part of lists/code
    formatted = formatted.replace(/\n/g, '<br/>');

    // Clean up extra br tags adjacent to lists
    formatted = formatted.replace(/<br\/>(<ul|<ol|<\/ul>|<\/ol>)/g, '$1');
    formatted = formatted.replace(/(<\/ul>|<\/ol>)<br\/>/g, '$1');

    return formatted;
  };

  return (
    <div className={`vb-msg ${isBot ? 'vb-msg--bot' : 'vb-msg--user'} ${isNew ? 'vb-msg--new' : ''}`}>
      {isBot && (
        <div className="vb-msg-avatar">
          <IconBot />
        </div>
      )}
      <div className="vb-msg-bubble">
        <div
          className="vb-msg-text"
          dangerouslySetInnerHTML={{ __html: formatText(msg.text) }}
        />
        <div className="vb-msg-time">
          {new Date(msg.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────
   MAIN CHATBOT COMPONENT
───────────────────────────────────────── */
export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [newMsgIds, setNewMsgIds] = useState(new Set(['welcome']));
  const [unread, setUnread] = useState(0);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  /* Auto-scroll to latest message */
  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, open]);

  /* Focus input when opened */
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 300);
      setUnread(0);
    }
  }, [open]);

  const addMessage = useCallback((role, text) => {
    const id = `${role}-${Date.now()}-${Math.random()}`;
    const msg = { id, role, text, ts: Date.now() };
    setMessages(prev => [...prev, msg]);
    setNewMsgIds(prev => new Set([...prev, id]));
    // Remove "new" animation class after it plays
    setTimeout(() => {
      setNewMsgIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }, 600);
    return id;
  }, []);

  const sendMessage = useCallback(async (text) => {
    const query = (text || input).trim();
    if (!query || loading) return;

    setInput('');
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
    setError(null);
    addMessage('user', query);
    setLoading(true);

    if (!open) setUnread(prev => prev + 1);

    abortRef.current = new AbortController();

    try {
      const res = await fetch(CHATBOT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = '';
      let botText = '';
      let botMsgId = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });
        const events = sseBuffer.split('\n\n');
        sseBuffer = events.pop() || '';

        for (const event of events) {
          const line = event.split('\n').find(l => l.startsWith('data: '));
          if (!line) continue;
          const payload = line.slice(6).trim();
          if (payload === '[DONE]') continue;

          let parsed;
          try {
            parsed = JSON.parse(payload);
          } catch {
            continue;
          }

          if (parsed.error) throw new Error(parsed.error);

          if (parsed.content) {
            botText += parsed.content;
            if (botMsgId === null) {
              setLoading(false);
              botMsgId = addMessage('bot', botText);
            } else {
              const id = botMsgId;
              setMessages(prev => prev.map(m => (m.id === id ? { ...m, text: botText } : m)));
            }
          }
        }
      }

      if (botMsgId === null) {
        addMessage('bot', 'Sorry, I got an empty response.');
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || 'Connection failed. Make sure the chatbot service is running.');
      addMessage('bot', '⚠️ Something went wrong. Please try again in a moment.');
    } finally {
      setLoading(false);
    }
  }, [input, loading, open, addMessage]);

  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 100)}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleClear = () => {
    abortRef.current?.abort();
    setMessages([WELCOME_MSG]);
    setNewMsgIds(new Set(['welcome']));
    setError(null);
    setLoading(false);
    setInput('');
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  };

  const handleClose = () => {
    setOpen(false);
    abortRef.current?.abort();
  };

  return (
    <>
      {/* ── CHAT WINDOW ── */}
      <div className={`vb-window ${open ? 'vb-window--open' : ''}`} role="dialog" aria-label="VitroFit Chatbot">

        {/* Header */}
        <div className="vb-header">
          <div className="vb-header-left">
            <div className="vb-header-avatar">
              <IconBot />
              <span className="vb-header-status-dot" />
            </div>
            <div className="vb-header-info">
              <div className="vb-header-name">VitroBot</div>
              <div className="vb-header-sub">AI Fitness Assistant</div>
            </div>
          </div>
          <div className="vb-header-actions">
            <button className="vb-icon-btn" onClick={handleClear} title="Clear chat" aria-label="Clear chat">
              <IconClear />
            </button>
            <button className="vb-icon-btn" onClick={handleClose} title="Minimise" aria-label="Close chat">
              <IconChevron />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="vb-messages">
          {messages.map(msg => (
            <MessageBubble key={msg.id} msg={msg} isNew={newMsgIds.has(msg.id)} />
          ))}
          {loading && <TypingDots />}
          {error && (
            <div className="vb-error">
              <span>⚠ {error}</span>
              <button onClick={() => setError(null)}>Dismiss</button>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick prompts — only show when just the welcome msg is visible */}
        {messages.length === 1 && !loading && (
          <div className="vb-quick-prompts">
            {QUICK_PROMPTS.map(q => (
              <button
                key={q}
                className="vb-quick-btn"
                onClick={() => sendMessage(q)}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input area */}
        <div className="vb-input-area">
          <div className="vb-input-wrap">
            <textarea
              ref={inputRef}
              className="vb-input"
              placeholder="Ask me about workouts, nutrition…"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              rows={1}
              maxLength={1000}
              disabled={loading}
              aria-label="Chat input"
            />
            <button
              className={`vb-send-btn ${input.trim() && !loading ? 'vb-send-btn--active' : ''}`}
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              aria-label="Send message"
            >
              <IconSend />
            </button>
          </div>
          <div className="vb-input-hint">
            Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line
          </div>
        </div>
      </div>

      {/* ── FAB TOGGLE BUTTON ── */}
      <button
        className={`vb-fab ${open ? 'vb-fab--open' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-label={open ? 'Close chatbot' : 'Open chatbot'}
        title="VitroBot — AI Fitness Assistant"
      >
        <span className="vb-fab-icon vb-fab-icon--chat">
          <IconBot />
        </span>
        <span className="vb-fab-icon vb-fab-icon--close">
          <IconClose />
        </span>
        {!open && unread > 0 && (
          <span className="vb-fab-badge">{unread}</span>
        )}
        {/* Pulse rings */}
        <span className="vb-fab-ring vb-fab-ring--1" />
        <span className="vb-fab-ring vb-fab-ring--2" />
      </button>
    </>
  );
}

