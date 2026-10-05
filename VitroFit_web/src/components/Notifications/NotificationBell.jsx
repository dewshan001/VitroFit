import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../../api/notifications';
import './NotificationBell.css';

const POLL_MS = 30000;

const ICONS = {
  'timetable.verified': '✓',
  'timetable.rejected': '!',
  'timetable.review-requested': '⏱',
};

function timeAgo(iso) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return days < 7 ? `${days} d ago` : new Date(iso).toLocaleDateString();
}

/** Bell with an unread badge for the signed-in user's in-app notifications. */
export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [failed, setFailed] = useState(false);
  const rootRef = useRef(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      const data = await getNotifications();
      setItems(data.items || []);
      setUnread(data.unreadCount || 0);
      setFailed(false);
    } catch {
      setFailed(true); // keep whatever was shown; the next poll retries
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  // Refresh as soon as the menu opens so it is never stale.
  useEffect(() => { if (open) load(); }, [open, load]);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const openItem = async (item) => {
    setOpen(false);
    if (!item.isRead) {
      setItems((list) => list.map((n) => (n.id === item.id ? { ...n, isRead: true } : n)));
      setUnread((n) => Math.max(0, n - 1));
      markNotificationRead(item.id).catch(() => {});
    }
    if (item.linkUrl && item.linkUrl.startsWith('/')) navigate(item.linkUrl);
  };

  const readAll = async () => {
    setItems((list) => list.map((n) => ({ ...n, isRead: true })));
    setUnread(0);
    markAllNotificationsRead().catch(() => load());
  };

  return (
    <div className="nb-root" ref={rootRef}>
      <button
        type="button"
        className={`nb-btn ${unread > 0 ? 'nb-btn--unread' : ''}`}
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.7 21a2 2 0 01-3.4 0" />
        </svg>
        {unread > 0 && <span className="nb-badge">{unread > 9 ? '9+' : unread}</span>}
      </button>

      {open && (
        <div className="nb-menu" role="menu" aria-label="Notifications">
          <div className="nb-head">
            <strong>Notifications</strong>
            {unread > 0 && <button type="button" className="nb-link" onClick={readAll}>Mark all read</button>}
          </div>

          {items.length === 0 ? (
            <p className="nb-empty">{failed ? 'Could not load notifications.' : 'You are all caught up.'}</p>
          ) : (
            <ul className="nb-list">
              {items.map((n) => (
                <li key={n.id}>
                  <button type="button" role="menuitem" className={`nb-item ${n.isRead ? '' : 'nb-item--unread'}`} onClick={() => openItem(n)}>
                    <span className={`nb-icon nb-icon--${(n.type.split('.')[1] || 'info')}`} aria-hidden="true">{ICONS[n.type] || 'i'}</span>
                    <span className="nb-text">
                      <span className="nb-title">{n.title}</span>
                      <span className="nb-msg">{n.message}</span>
                      <span className="nb-time">{timeAgo(n.createdAt)}</span>
                    </span>
                    {!n.isRead && <span className="nb-dot" aria-label="Unread" />}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
