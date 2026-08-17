import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { changePassword, uploadProfileImage, deleteAccount } from '../api/auth';
import PhotoUploadModal from '../components/PhotoUploadModal/PhotoUploadModal';
import './ProfilePage.css';

/* ── Avatar helpers ── */
const AVATAR_COLOURS = [
  '#c8f000', '#00e5ff', '#ff6b35', '#a855f7',
  '#f43f5e', '#10b981', '#f59e0b', '#3b82f6',
];
const avatarColor = (name = '') =>
  AVATAR_COLOURS[(name.charCodeAt(0) || 0) % AVATAR_COLOURS.length];
const initials = (name = '') =>
  name.split(' ').slice(0, 2).map((w) => w[0]?.toUpperCase() ?? '').join('');

const TABS = ['Overview', 'Edit Profile', 'Settings'];

/* ── Fake activity feed ── */
const ACTIVITY = [
  { icon: '🏋️', text: 'Completed HIIT Blast class', time: '2 hours ago' },
  { icon: '🔥', text: 'Hit a 5-day workout streak!', time: 'Yesterday' },
  { icon: '📅', text: 'Booked Yoga Flow — Saturday 9 AM', time: '2 days ago' },
  { icon: '⚡', text: 'Earned 50 VitroPoints', time: '3 days ago' },
  { icon: '🏆', text: 'Completed "First Month" challenge', time: '1 week ago' },
];

/* ── Fake goals ── */
const DEFAULT_GOALS = [
  { label: 'Attend 20 classes this month', done: true },
  { label: 'Maintain 7-day streak', done: false },
  { label: 'Try 3 different class types', done: true },
  { label: 'Complete nutrition challenge', done: false },
];

export default function ProfilePage() {
  const { auth, isLoggedIn, updateUser, logout, getFullName } = useAuth();
  const navigate      = useNavigate();
  const [params]      = useSearchParams();
  const initTab       = TABS.indexOf(params.get('tab') === 'settings' ? 'Settings' : 'Overview');
  const [activeTab, setActiveTab]   = useState(initTab >= 0 ? initTab : 0);
  const [goals, setGoals]           = useState(DEFAULT_GOALS);
  const headerRef                   = useRef(null);

  /* ── Derive user fields from DB response ── */
  const user      = auth?.user ?? {};
  // firstName / lastName come from the DB (camelCase or PascalCase)
  const firstName = user.firstName || user.FirstName || '';
  const lastName  = user.lastName  || user.LastName  || '';
  const fullName  = getFullName();
  const email     = user.email     || user.Email     || '';
  const phone     = user.phone     || user.Phone     || '';
  const color     = avatarColor(fullName);
  const ini       = initials(fullName);

  /* ── Edit Profile form ── */
  const imageUrl = user.profileImageUrl || user.ProfileImageUrl || '';
  const [form, setForm] = useState({
    firstName,
    lastName,
    phone,
    bio:   user.bio   || '',
    goal:  user.goal  || 'Lose Weight',
    level: user.level || 'Intermediate',
  });
  const [saveMsg, setSaveMsg]           = useState('');
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadMsg, setUploadMsg]         = useState('');
  const [photoModalOpen, setPhotoModalOpen] = useState(false);

  /* ── Change Password form ── */
  const [pwForm, setPwForm]     = useState({ current: '', newPw: '', confirm: '' });
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMsg, setPwMsg]         = useState({ text: '', ok: false });

  /* ── Notifications ── */
  const [notifications, setNotifications] = useState({
    email: true, sms: false, push: true, newsletter: false,
  });

  /* Scroll parallax */
  useEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const onScroll = () => {
      el.style.backgroundPositionY = `${window.scrollY * 0.4}px`;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  /* Redirect if not logged in */
  useEffect(() => {
    if (!isLoggedIn) navigate('/login');
  }, [isLoggedIn, navigate]);

  if (!isLoggedIn) return null;

  /* ── Handlers ── */
  const handleSaveProfile = (e) => {
    e.preventDefault();
    // Persist to sessionStorage (merges firstName/lastName so getFullName keeps working)
    updateUser({
      firstName: form.firstName,
      lastName:  form.lastName,
      phone:     form.phone,
      bio:       form.bio,
      goal:      form.goal,
      level:     form.level,
    });
    setSaveMsg('✓ Profile updated successfully!');
    setTimeout(() => setSaveMsg(''), 3000);
  };

  const handleUploadPhoto = async (file) => {
    if (!file) return;

    /* URL-only path (pasted URL, not a File object) */
    if (file._isUrl) {
      updateUser({ profileImageUrl: file.url });
      setUploadMsg('✓ Profile photo updated successfully!');
      setTimeout(() => { setUploadMsg(''); setPhotoModalOpen(false); }, 1800);
      return;
    }

    setUploadingPhoto(true);
    setUploadMsg('');

    try {
      const data = await uploadProfileImage(file);
      const url = data.profileImageUrl || '';
      if (!url) throw new Error('Upload returned no image URL.');
      updateUser({ profileImageUrl: url });
      setUploadMsg('✓ Profile photo updated successfully!');
      setTimeout(() => { setUploadMsg(''); setPhotoModalOpen(false); }, 1800);
    } catch (err) {
      setUploadMsg(err?.message || 'Failed to upload profile photo.');
    } finally {
      setUploadingPhoto(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwMsg({ text: '', ok: false });

    if (!pwForm.current) {
      setPwMsg({ text: 'Current password is required.', ok: false }); return;
    }
    if (pwForm.newPw.length < 6) {
      setPwMsg({ text: 'New password must be at least 6 characters.', ok: false }); return;
    }
    if (pwForm.newPw !== pwForm.confirm) {
      setPwMsg({ text: 'Passwords do not match.', ok: false }); return;
    }

    setPwLoading(true);
    try {
      await changePassword({ currentPassword: pwForm.current, newPassword: pwForm.newPw });
      setPwMsg({ text: '✓ Password changed successfully!', ok: true });
      setPwForm({ current: '', newPw: '', confirm: '' });
    } catch (err) {
      setPwMsg({ text: err.message || 'Failed to change password.', ok: false });
    } finally {
      setPwLoading(false);
    }
  };

  /* ── Delete Account state ── */
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting]             = useState(false);
  const [deleteError, setDeleteError]       = useState('');

  const handleLogout = () => { logout(); navigate('/login'); };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    setDeleteError('');
    try {
      await deleteAccount();
      logout();
      navigate('/register');
    } catch (err) {
      setDeleteError(err?.message || 'Failed to delete account. Please try again.');
      setDeleting(false);
    }
  };

  const toggleGoal = (i) =>
    setGoals((g) => g.map((item, idx) => idx === i ? { ...item, done: !item.done } : item));

  return (
    <main className="profile-page">
      {/* Hero header */}
      <div className="pp-page-header" ref={headerRef}>
        <div className="pp-page-header-overlay" />
        <div className="pp-page-header-content container">
          <div
            className="pp-page-avatar"
            style={{ '--av-color': color, '--av-bg': color + '22' }}
          >
            {imageUrl ? (
              <img src={imageUrl} alt={`${fullName || 'Profile'} photo`} className="pp-page-avatar-img" />
            ) : (
              ini
            )}
            <span className="pp-page-avatar-ring" />
          </div>
          <div className="pp-page-hero-info">
            <p className="section-label">Member Profile</p>
            <h1 className="pp-page-name">{fullName || 'Athlete'}</h1>
            <p className="pp-page-email">{email}</p>
            <span className="pp-page-plan">{user.plan || 'Free Plan'}</span>
          </div>
        </div>
        {/* Stats strip */}
        <div className="pp-page-stats container">
          {[
            { val: user.classesAttended ?? 0, label: 'Classes' },
            { val: user.streakDays       ?? 0, label: 'Day Streak' },
            { val: user.points           ?? 0, label: 'VitroPoints' },
            { val: user.memberSince      || '2026', label: 'Member Since' },
          ].map(({ val, label }) => (
            <div className="pp-page-stat" key={label}>
              <span className="pp-page-stat-val">{val}</span>
              <span className="pp-page-stat-label">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Tab bar */}
      <div className="pp-tabs-bar">
        <div className="container pp-tabs-inner">
          {TABS.map((t, i) => (
            <button
              key={t}
              className={`pp-tab ${activeTab === i ? 'pp-tab--active' : ''}`}
              onClick={() => setActiveTab(i)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="container pp-content">

        {/* ══════ OVERVIEW ══════ */}
        {activeTab === 0 && (
          <div className="pp-grid">
            {/* Activity feed */}
            <section className="pp-card pp-card--full">
              <h2 className="pp-card-title">Recent Activity</h2>
              <ul className="pp-activity-list">
                {ACTIVITY.map(({ icon, text, time }, i) => (
                  <li key={i} className="pp-activity-item" style={{ animationDelay: `${i * 0.07}s` }}>
                    <span className="pp-act-icon">{icon}</span>
                    <span className="pp-act-text">{text}</span>
                    <span className="pp-act-time">{time}</span>
                  </li>
                ))}
              </ul>
            </section>

            {/* Goals */}
            <section className="pp-card">
              <h2 className="pp-card-title">My Goals</h2>
              <ul className="pp-goals-list">
                {goals.map(({ label, done }, i) => (
                  <li key={i} className="pp-goal-item">
                    <button
                      className={`pp-goal-check ${done ? 'done' : ''}`}
                      onClick={() => toggleGoal(i)}
                      aria-label={done ? 'Mark incomplete' : 'Mark complete'}
                    >
                      {done && (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polyline points="20 6 9 17 4 12"/>
                        </svg>
                      )}
                    </button>
                    <span className={done ? 'pp-goal-done' : ''}>{label}</span>
                  </li>
                ))}
              </ul>
            </section>

            {/* Quick info */}
            <section className="pp-card">
              <h2 className="pp-card-title">Quick Info</h2>
              <ul className="pp-info-list">
                <li><span>First Name</span><strong>{firstName || '—'}</strong></li>
                <li><span>Last Name</span><strong>{lastName || '—'}</strong></li>
                <li><span>Fitness Goal</span><strong>{user.goal || 'Lose Weight'}</strong></li>
                <li><span>Level</span><strong>{user.level || 'Intermediate'}</strong></li>
                <li><span>Phone</span><strong>{phone || '—'}</strong></li>
                <li>
                  <span>Bio</span>
                  <strong className="pp-bio-preview">{user.bio || 'No bio yet — add one in Edit Profile.'}</strong>
                </li>
              </ul>
              <button className="pp-mini-btn" onClick={() => setActiveTab(1)}>Edit Profile →</button>
            </section>
          </div>
        )}

        {/* ══════ EDIT PROFILE ══════ */}
        {activeTab === 1 && (
          <div className="pp-form-wrap">
            <form className="pp-form" onSubmit={handleSaveProfile}>
              {/* Name row */}
              <div className="pp-form-row">
                <div className="pp-form-group">
                  <label htmlFor="pf-firstname">First Name</label>
                  <input
                    id="pf-firstname"
                    type="text"
                    className="pp-input"
                    value={form.firstName}
                    onChange={(e) => setForm((f) => ({ ...f, firstName: e.target.value }))}
                    placeholder="John"
                  />
                </div>
                <div className="pp-form-group">
                  <label htmlFor="pf-lastname">Last Name</label>
                  <input
                    id="pf-lastname"
                    type="text"
                    className="pp-input"
                    value={form.lastName}
                    onChange={(e) => setForm((f) => ({ ...f, lastName: e.target.value }))}
                    placeholder="Doe"
                  />
                </div>
              </div>

              <div className="pp-form-group">
                <label htmlFor="pf-email">Email <span className="pp-readonly-note">(read-only)</span></label>
                <input
                  id="pf-email"
                  type="email"
                  className="pp-input pp-input--readonly"
                  value={email}
                  readOnly
                  tabIndex={-1}
                />
              </div>

              <div className="pp-form-group">
                <label htmlFor="pf-phone">Phone</label>
                <input
                  id="pf-phone"
                  type="tel"
                  className="pp-input"
                  value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  placeholder="+1 234 567 8900"
                />
              </div>
              <div className="pp-form-group">
                <label htmlFor="pf-bio">Bio</label>
                <textarea
                  id="pf-bio"
                  className="pp-input pp-textarea"
                  rows="4"
                  value={form.bio}
                  onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
                  placeholder="Tell us a little about yourself…"
                />
              </div>

              <div className="pp-form-group">
                <label>Profile Photo</label>
                <button
                  type="button"
                  className="pp-photo-trigger"
                  onClick={() => setPhotoModalOpen(true)}
                >
                  {imageUrl
                    ? <img src={imageUrl} alt="Current avatar" className="pp-photo-trigger-thumb" />
                    : <span className="pp-photo-trigger-initials" style={{ background: color + '22', color }}>{ini || '?'}</span>
                  }
                  <span className="pp-photo-trigger-text">
                    <span className="pp-photo-trigger-label">Change Profile Photo</span>
                    <span className="pp-photo-trigger-hint">Click to open photo uploader</span>
                  </span>
                  <svg className="pp-photo-trigger-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </button>
                {uploadMsg && <p className="pp-upload-msg">{uploadMsg}</p>}
              </div>

              <div className="pp-form-row">
                <div className="pp-form-group">
                  <label htmlFor="pf-goal">Fitness Goal</label>
                  <select
                    id="pf-goal"
                    className="pp-input pp-select"
                    value={form.goal}
                    onChange={(e) => setForm((f) => ({ ...f, goal: e.target.value }))}
                  >
                    {['Lose Weight', 'Build Muscle', 'Improve Endurance', 'Stay Active', 'Flexibility'].map((g) => (
                      <option key={g}>{g}</option>
                    ))}
                  </select>
                </div>
                <div className="pp-form-group">
                  <label htmlFor="pf-level">Fitness Level</label>
                  <select
                    id="pf-level"
                    className="pp-input pp-select"
                    value={form.level}
                    onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}
                  >
                    {['Beginner', 'Intermediate', 'Advanced', 'Elite'].map((l) => (
                      <option key={l}>{l}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pp-form-actions">
                <button id="save-profile" type="submit" className="btn-primary">
                  Save Changes <span className="btn-arrow">→</span>
                </button>
                {saveMsg && <span className="pp-save-msg">{saveMsg}</span>}
              </div>
            </form>
          </div>
        )}

        {/* ══════ SETTINGS ══════ */}
        {activeTab === 2 && (
          <div className="pp-settings-wrap">

            {/* Change password */}
            <section className="pp-card pp-card--full">
              <h2 className="pp-card-title">Change Password</h2>
              <form className="pp-pw-form" onSubmit={handleChangePassword}>
                <div className="pp-form-row">
                  <div className="pp-form-group">
                    <label htmlFor="pw-current">Current Password</label>
                    <input
                      id="pw-current"
                      type="password"
                      className="pp-input"
                      placeholder="••••••••"
                      value={pwForm.current}
                      onChange={(e) => setPwForm((p) => ({ ...p, current: e.target.value }))}
                      autoComplete="current-password"
                    />
                  </div>
                  <div className="pp-form-group">
                    <label htmlFor="pw-new">New Password</label>
                    <input
                      id="pw-new"
                      type="password"
                      className="pp-input"
                      placeholder="Min. 6 characters"
                      value={pwForm.newPw}
                      onChange={(e) => setPwForm((p) => ({ ...p, newPw: e.target.value }))}
                      autoComplete="new-password"
                    />
                  </div>
                  <div className="pp-form-group">
                    <label htmlFor="pw-confirm">Confirm New Password</label>
                    <input
                      id="pw-confirm"
                      type="password"
                      className="pp-input"
                      placeholder="Repeat new password"
                      value={pwForm.confirm}
                      onChange={(e) => setPwForm((p) => ({ ...p, confirm: e.target.value }))}
                      autoComplete="new-password"
                    />
                  </div>
                </div>

                {/* Inline password strength indicator */}
                {pwForm.newPw && (
                  <div className="pp-pw-strength">
                    {['Weak', 'Fair', 'Good', 'Strong'].map((label, idx) => {
                      const strength = pwForm.newPw.length < 6 ? 0
                        : pwForm.newPw.length < 8 ? 1
                        : /[A-Z]/.test(pwForm.newPw) && /\d/.test(pwForm.newPw) ? 3
                        : 2;
                      return (
                        <span
                          key={label}
                          className={`pp-pw-bar ${idx <= strength ? `pp-pw-bar--${['weak','fair','good','strong'][strength]}` : ''}`}
                        />
                      );
                    })}
                    <span className="pp-pw-strength-label">
                      {pwForm.newPw.length < 6 ? 'Weak'
                        : pwForm.newPw.length < 8 ? 'Fair'
                        : /[A-Z]/.test(pwForm.newPw) && /\d/.test(pwForm.newPw) ? 'Strong'
                        : 'Good'}
                    </span>
                  </div>
                )}

                <div className="pp-form-actions" style={{ marginTop: '1.25rem' }}>
                  <button
                    id="change-password-submit"
                    type="submit"
                    className={`btn-primary ${pwLoading ? 'loading' : ''}`}
                    disabled={pwLoading}
                  >
                    {pwLoading
                      ? <span className="pp-spinner" />
                      : <> Update Password <span className="btn-arrow">→</span></>
                    }
                  </button>
                  {pwMsg.text && (
                    <span className={pwMsg.ok ? 'pp-save-msg' : 'pp-error-msg'}>
                      {pwMsg.text}
                    </span>
                  )}
                </div>
              </form>
            </section>

            {/* Notifications */}
            <section className="pp-card pp-card--full">
              <h2 className="pp-card-title">Notifications</h2>
              <div className="pp-toggles">
                {Object.entries(notifications).map(([key, val]) => (
                  <label key={key} className="pp-toggle-row">
                    <span>{key.charAt(0).toUpperCase() + key.slice(1)} Notifications</span>
                    <button
                      role="switch"
                      aria-checked={val}
                      className={`pp-toggle ${val ? 'pp-toggle--on' : ''}`}
                      onClick={() => setNotifications((n) => ({ ...n, [key]: !n[key] }))}
                    >
                      <span className="pp-toggle-thumb" />
                    </button>
                  </label>
                ))}
              </div>
            </section>

            {/* Danger zone */}
            <section className="pp-card pp-card--full pp-danger-zone">
              <h2 className="pp-card-title pp-danger-title">Danger Zone</h2>
              <p className="pp-danger-desc">
                Signing out will end your current session. Deleting your account is permanent.
              </p>
              <div className="pp-danger-actions">
                <button className="pp-btn-danger-outline" onClick={handleLogout}>Sign Out</button>
                <button className="pp-btn-danger" onClick={() => setDeleteModalOpen(true)}>Delete Account</button>
              </div>
            </section>
          </div>
        )}

      </div>

      {/* ── Photo Upload Modal ── */}
      <PhotoUploadModal
        isOpen={photoModalOpen}
        onClose={() => { if (!uploadingPhoto) setPhotoModalOpen(false); }}
        onUpload={handleUploadPhoto}
        uploading={uploadingPhoto}
        uploadMsg={uploadMsg}
      />

      {/* ── Delete Account Confirmation Modal ── */}
      {deleteModalOpen && (
        <div className="pp-delete-overlay" onClick={() => !deleting && setDeleteModalOpen(false)}>
          <div className="pp-delete-modal" onClick={(e) => e.stopPropagation()}>
            <div className="pp-delete-header">
              <div className="pp-delete-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6" />
                </svg>
              </div>
              <h3>Delete Account?</h3>
            </div>
            <p className="pp-delete-desc">
              Are you sure you want to delete your account? This action is <strong>permanent</strong> and cannot be undone. All your workout records, bookings, and profile data will be permanently removed.
            </p>
            {deleteError && <div className="pp-delete-error">{deleteError}</div>}
            <div className="pp-delete-actions">
              <button
                type="button"
                className="pp-delete-cancel"
                onClick={() => setDeleteModalOpen(false)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="pp-delete-confirm"
                onClick={handleDeleteAccount}
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Yes, Delete Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
