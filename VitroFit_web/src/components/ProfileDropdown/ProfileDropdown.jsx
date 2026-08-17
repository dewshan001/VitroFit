import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import './ProfileDropdown.css';

/* Deterministic avatar colour based on first letter */
const AVATAR_COLOURS = [
  '#c8f000', '#00e5ff', '#ff6b35', '#a855f7', '#f43f5e',
  '#10b981', '#f59e0b', '#3b82f6',
];
function avatarColor(name = '') {
  const idx = (name.charCodeAt(0) || 0) % AVATAR_COLOURS.length;
  return AVATAR_COLOURS[idx];
}
function initials(name = '') {
  return name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

const QUICK_STATS = [
  { label: 'Classes', icon: '🏋️', key: 'classesAttended', fallback: 0 },
  { label: 'Streak',  icon: '🔥', key: 'streakDays',       fallback: 0 },
  { label: 'Points',  icon: '⚡', key: 'points',            fallback: 0 },
];

export default function ProfileDropdown() {
  const { auth, isLoggedIn, logout, getFullName } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen]           = useState(false);
  const [editMode, setEditMode]   = useState(false);
  const [nameVal, setNameVal]     = useState('');
  const dropRef                   = useRef(null);

  const user     = auth?.user ?? {};
  const fullName = getFullName();
  const email    = user.email || user.Email || '';
  const imageUrl = user.profileImageUrl || user.ProfileImageUrl || '';
  const color    = avatarColor(fullName);
  const ini      = initials(fullName);
  const plan     = user.plan || 'Free Plan';

  /* Close on outside click */
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (dropRef.current && !dropRef.current.contains(e.target)) {
        setOpen(false);
        setEditMode(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  /* Close on Escape */
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') { setOpen(false); setEditMode(false); }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  if (!isLoggedIn) return null;

  const handleLogout = () => {
    setOpen(false);
    logout();
    navigate('/login');
  };

  const handleSaveName = () => {
    if (!nameVal.trim()) return;
    const newAuth = { ...auth, user: { ...auth.user, fullName: nameVal.trim() } };
    sessionStorage.setItem('vitrofitAuth', JSON.stringify(newAuth));
    window.dispatchEvent(new Event('vitrofit-auth-change'));
    setEditMode(false);
  };

  return (
    <div className="profile-dropdown-root" ref={dropRef}>
      {/* ── Avatar trigger ── */}
      <button
        className={`profile-avatar-btn ${open ? 'active' : ''}`}
        onClick={() => { setOpen(!open); setEditMode(false); }}
        aria-label="Open profile menu"
        aria-expanded={open}
      >
        <span
          className="profile-avatar"
          style={{ '--avatar-color': color, '--avatar-bg': color + '22' }}
        >
          {imageUrl ? (
            <img src={imageUrl} alt={`${fullName || 'Profile'} photo`} className="profile-avatar-img" />
          ) : (
            ini
          )}
        </span>
        <span className="profile-avatar-chevron" style={{ transform: open ? 'rotate(180deg)' : 'none' }}>
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </span>
        {/* Online pulse */}
        <span className="profile-online-dot" />
      </button>

      {/* ── Drop panel ── */}
      <div className={`profile-panel ${open ? 'profile-panel--open' : ''}`}>
        {/* Header */}
        <div className="pp-header">
          <div
            className="pp-avatar-lg"
            style={{ '--avatar-color': color, '--avatar-bg': color + '22' }}
          >
            {imageUrl ? (
              <img src={imageUrl} alt={`${fullName || 'Profile'} photo`} className="pp-avatar-img" />
            ) : (
              ini
            )}
            <span className="pp-avatar-ring" />
          </div>
          <div className="pp-header-info">
            {editMode ? (
              <div className="pp-edit-name">
                <input
                  autoFocus
                  className="pp-name-input"
                  defaultValue={fullName}
                  onChange={(e) => setNameVal(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSaveName(); }}
                  placeholder="Your name"
                />
                <div className="pp-edit-actions">
                  <button className="pp-save-btn" onClick={handleSaveName}>Save</button>
                  <button className="pp-cancel-btn" onClick={() => setEditMode(false)}>✕</button>
                </div>
              </div>
            ) : (
              <>
                <p className="pp-name">{fullName}</p>
                <p className="pp-email">{email}</p>
              </>
            )}
            <span className="pp-plan-badge">{plan}</span>
          </div>
          <button
            className="pp-edit-trigger"
            onClick={() => setEditMode(!editMode)}
            title="Edit profile"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
        </div>

        {/* Quick stats */}
        <div className="pp-stats">
          {QUICK_STATS.map(({ label, icon, key, fallback }) => (
            <div className="pp-stat" key={key}>
              <span className="pp-stat-icon">{icon}</span>
              <span className="pp-stat-val">{user[key] ?? fallback}</span>
              <span className="pp-stat-label">{label}</span>
            </div>
          ))}
        </div>

        {/* Divider */}
        <div className="pp-divider" />

        {/* Menu links */}
        <nav className="pp-nav">
          <Link to="/profile"    className="pp-link" onClick={() => setOpen(false)}>
            <svg className="pp-link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>
            My Profile
            <svg className="pp-link-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
          </Link>
          <Link to="/timetable"  className="pp-link" onClick={() => setOpen(false)}>
            <svg className="pp-link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
            My Classes
            <svg className="pp-link-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
          </Link>
          <Link to="/#pricing"   className="pp-link" onClick={() => setOpen(false)}>
            <svg className="pp-link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14 2 9.27l6.91-1.01z"/></svg>
            Membership
            <svg className="pp-link-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
          </Link>
          <Link to="/profile?tab=settings" className="pp-link" onClick={() => setOpen(false)}>
            <svg className="pp-link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            Settings
            <svg className="pp-link-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
          </Link>
          {(user.role === 2 || user.role === 'Admin') && (
            <Link to="/admin" className="pp-link" onClick={() => setOpen(false)} style={{ color: 'var(--accent)' }}>
              <svg className="pp-link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
              Admin Dashboard
              <svg className="pp-link-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 18l6-6-6-6"/></svg>
            </Link>
          )}
        </nav>

        <div className="pp-divider" />

        {/* Logout */}
        <button className="pp-logout" onClick={handleLogout}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
          </svg>
          Sign Out
        </button>
      </div>
    </div>
  );
}
