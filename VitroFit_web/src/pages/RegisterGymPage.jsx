import { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import './AuthPages.css';
import './RegisterGymPage.css';
import { verifyEmail, resendVerification } from '../api/auth';
import { registerGymOwner, GYM_LIMITS } from '../api/gymOwner';

const STEPS = ['Account', 'Gym', 'Equipment', 'Photos', 'Review', 'Verify'];

const EQUIPMENT_SUGGESTIONS = [
  'Treadmill', 'Elliptical', 'Stationary bike', 'Rowing machine', 'Squat rack', 'Smith machine',
  'Dumbbells', 'Barbells', 'Cable machine', 'Leg press', 'Bench press', 'Kettlebells', 'Pull-up bar',
];
const CLASS_SUGGESTIONS = ['Yoga', 'HIIT', 'Zumba', 'Spin', 'Pilates', 'CrossFit', 'Boxing', 'Strength basics'];

const HOW_IT_WORKS = [
  ['Apply', 'Tell us about your gym: details, website, equipment and photos.'],
  ['Verify your email', 'Confirm your address with a 6-digit code.'],
  ['We review it', 'An admin checks your application and emails you the decision.'],
  ['Go live', 'Once approved, sign in and verify your gym for members to find.'],
];

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9 ()-]{7,20}$/;

const formatBytes = (bytes) => (bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

/** Looks at the file's first bytes (not its name) to tell what it really is, like the server does. */
async function sniffKind(file) {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const at = (i, ...values) => values.every((v, k) => bytes[i + k] === v);
  if (at(0, 0xFF, 0xD8, 0xFF)) return 'jpeg';
  if (at(0, 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)) return 'png';
  if (at(0, 0x52, 0x49, 0x46, 0x46) && at(8, 0x57, 0x45, 0x42, 0x50)) return 'webp';
  if (at(0, 0x25, 0x50, 0x44, 0x46, 0x2D)) return 'pdf';
  return 'unknown';
}

function isHttpsUrl(value) {
  try {
    const url = new URL(value.trim());
    return url.protocol === 'https:' && url.hostname.includes('.') && !url.username;
  } catch {
    return false;
  }
}

/* ── Tag input (equipment / classes) ──────────────────────────────── */
function TagInput({ id, label, hint, tags, onChange, suggestions, max, error, required }) {
  const [draft, setDraft] = useState('');

  const add = (raw) => {
    const value = raw.trim();
    if (!value) return;
    if (value.length > GYM_LIMITS.maxTagLength) return;
    if (tags.some((t) => t.toLowerCase() === value.toLowerCase())) return;
    if (tags.length >= max) return;
    onChange([...tags, value]);
  };

  const commit = () => {
    draft.split(',').forEach(add);
    setDraft('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Backspace' && !draft && tags.length) {
      onChange(tags.slice(0, -1));
    }
  };

  const remaining = suggestions.filter((s) => !tags.some((t) => t.toLowerCase() === s.toLowerCase()));

  return (
    <div className={`rg-field ${error ? 'rg-field--error' : ''}`}>
      <label htmlFor={id} className="rg-label">
        {label}{required && <span className="rg-req"> *</span>}
        <span className="rg-count">{tags.length}/{max}</span>
      </label>
      <div className="rg-tags-box" onClick={() => document.getElementById(id)?.focus()}>
        {tags.map((tag) => (
          <span className="rg-tag" key={tag}>
            {tag}
            <button type="button" aria-label={`Remove ${tag}`} onClick={() => onChange(tags.filter((t) => t !== tag))}>×</button>
          </span>
        ))}
        <input
          id={id}
          className="rg-tags-input"
          value={draft}
          maxLength={GYM_LIMITS.maxTagLength}
          placeholder={tags.length ? 'Add another…' : hint}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={commit}
          disabled={tags.length >= max}
        />
      </div>
      {remaining.length > 0 && tags.length < max && (
        <div className="rg-suggest" aria-label={`Suggested ${label.toLowerCase()}`}>
          <span>Quick add:</span>
          {remaining.slice(0, 10).map((s) => (
            <button type="button" key={s} onClick={() => add(s)}>+ {s}</button>
          ))}
        </div>
      )}
      {error && <span className="auth-error">{error}</span>}
    </div>
  );
}

/* ── Photo drop zone ──────────────────────────────────────────────── */
function PhotoZone({ id, title, help, photos, onAdd, onRemove, error }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const full = photos.length >= GYM_LIMITS.maxPhotos;

  const handleFiles = (list) => {
    if (list && list.length) onAdd(Array.from(list));
  };

  return (
    <div className={`rg-field ${error ? 'rg-field--error' : ''}`}>
      <span className="rg-label">
        {title}<span className="rg-req"> *</span>
        <span className="rg-count">{photos.length}/{GYM_LIMITS.maxPhotos}</span>
      </span>

      <div
        className={`rg-drop ${dragging ? 'rg-drop--active' : ''} ${full ? 'rg-drop--full' : ''}`}
        onDragOver={(e) => { e.preventDefault(); if (!full) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); if (!full) handleFiles(e.dataTransfer.files); }}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path d="M4 16l4-4a2 2 0 013 0l5 5M14 14l1-1a2 2 0 013 0l2 2M4 5h16v14H4z" />
          <circle cx="9" cy="9" r="1.2" />
        </svg>
        <p>{full ? 'Maximum photos added' : 'Drag photos here or'}</p>
        {!full && (
          <button type="button" className="rg-drop-btn" onClick={() => inputRef.current?.click()}>Browse files</button>
        )}
        <small>{help}</small>
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept={GYM_LIMITS.imageTypes.join(',')}
          multiple
          hidden
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
        />
      </div>

      {photos.length > 0 && (
        <ul className="rg-thumbs">
          {photos.map((p) => (
            <li key={p.id}>
              <img src={p.url} alt={p.file.name} />
              <button type="button" aria-label={`Remove ${p.file.name}`} onClick={() => onRemove(p.id)}>×</button>
              <span title={p.file.name}>{formatBytes(p.file.size)}</span>
            </li>
          ))}
        </ul>
      )}
      {error && <span className="auth-error">{error}</span>}
    </div>
  );
}

export default function RegisterGymPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const params = new URLSearchParams(location.search);
  const reapply = params.get('reapply') === '1';

  const [step, setStep] = useState(1);
  const [done, setDone] = useState(null); // null | 'pending' | 'resubmitted'
  const [form, setForm] = useState({
    firstName: '', lastName: '', email: params.get('email') || '', phone: '',
    password: '', confirm: '', terms: false,
    gymName: '', ownerRole: 'Owner', address: '', city: '', gymPhone: '', contactEmail: '',
    website: '', openingHours: '', description: '', otp: '',
  });
  const [equipment, setEquipment] = useState([]);
  const [classes, setClasses] = useState([]);
  const [gymPhotos, setGymPhotos] = useState([]);
  const [equipmentPhotos, setEquipmentPhotos] = useState([]);
  const [license, setLicense] = useState(null);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [serverErrors, setServerErrors] = useState([]);
  const [notice, setNotice] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const cardRef = useRef(null);
  const licenseRef = useRef(null);
  const photoUrls = useRef(new Set());

  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
    if (errors[key]) setErrors((er) => ({ ...er, [key]: undefined }));
  };

  /* Fade in + scroll to #how-it-works when linked from the Find Gyms banner. */
  useEffect(() => {
    const t = setTimeout(() => cardRef.current?.closest('.auth-card-wrap')?.classList.add('visible'), 60);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (location.hash === '#how-it-works') {
      setTimeout(() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
    } else {
      window.scrollTo(0, 0); // arriving from the Find Gyms banner keeps the old scroll position otherwise
    }
  }, [location.hash]);

  /* Release preview URLs when leaving the page. */
  useEffect(() => {
    const urls = photoUrls.current;
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, []);

  const scrollCardTop = () => cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  /* ── Photos ─────────────────────────────────────────────────────── */
  const addPhotos = useCallback(async (kind, files) => {
    const setList = kind === 'gym' ? setGymPhotos : setEquipmentPhotos;
    const current = kind === 'gym' ? gymPhotos : equipmentPhotos;
    const problems = [];
    const accepted = [];
    const kinds = await Promise.all(files.map(sniffKind));

    files.forEach((file, i) => {
      if (!GYM_LIMITS.imageTypes.includes(file.type) || !['jpeg', 'png', 'webp'].includes(kinds[i])) {
        problems.push(`"${file.name}" is not a JPG, PNG or WebP image.`);
      } else if (file.size > GYM_LIMITS.maxImageBytes) {
        problems.push(`"${file.name}" is ${formatBytes(file.size)}; the limit is 5 MB.`);
      } else if (current.length + accepted.length >= GYM_LIMITS.maxPhotos) {
        problems.push(`Only ${GYM_LIMITS.maxPhotos} photos are allowed here.`);
      } else {
        const url = URL.createObjectURL(file);
        photoUrls.current.add(url);
        accepted.push({ id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`, file, url });
      }
    });

    if (accepted.length) setList((list) => [...list, ...accepted]);
    setErrors((er) => ({ ...er, [`${kind}Photos`]: problems.length ? [...new Set(problems)].join(' ') : undefined }));
  }, [gymPhotos, equipmentPhotos]);

  const removePhoto = (kind, id) => {
    const setList = kind === 'gym' ? setGymPhotos : setEquipmentPhotos;
    setList((list) => {
      const target = list.find((p) => p.id === id);
      if (target) { URL.revokeObjectURL(target.url); photoUrls.current.delete(target.url); }
      return list.filter((p) => p.id !== id);
    });
    setErrors((er) => ({ ...er, [`${kind}Photos`]: undefined }));
  };

  const pickLicense = async (file) => {
    if (!file) return;
    const kind = await sniffKind(file);
    if (!GYM_LIMITS.licenseTypes.includes(file.type) || !['pdf', 'jpeg', 'png'].includes(kind)) {
      setErrors((er) => ({ ...er, license: 'The licence must be a PDF, JPG or PNG file.' }));
    } else if (file.size > GYM_LIMITS.maxLicenseBytes) {
      setErrors((er) => ({ ...er, license: `The file is ${formatBytes(file.size)}; the limit is 5 MB.` }));
    } else {
      setLicense(file);
      setErrors((er) => ({ ...er, license: undefined }));
    }
  };

  /* ── Validation (mirrors GymApplicationValidator on the server) ─── */
  const validators = {
    1: () => {
      const e = {};
      if (!form.email.trim()) e.email = 'Email is required';
      else if (!EMAIL_RE.test(form.email.trim())) e.email = 'Enter a valid email';
      if (!form.password) e.password = 'Password is required';
      else if (form.password.length < 8) e.password = 'Minimum 8 characters';
      if (!reapply) {
        if (!form.firstName.trim()) e.firstName = 'First name required';
        if (!form.lastName.trim()) e.lastName = 'Last name required';
        if (!form.phone.trim()) e.phone = 'Phone number is required';
        else if (!PHONE_RE.test(form.phone.trim())) e.phone = 'Invalid phone number';
        if (!form.confirm) e.confirm = 'Please confirm your password';
        else if (form.confirm !== form.password) e.confirm = 'Passwords do not match';
        if (!form.terms) e.terms = 'You must accept the terms';
      }
      return e;
    },
    2: () => {
      const e = {};
      if (!form.gymName.trim()) e.gymName = 'Gym name is required';
      if (!form.address.trim()) e.address = 'Address is required';
      if (!form.city.trim()) e.city = 'City is required';
      if (!form.gymPhone.trim()) e.gymPhone = 'Gym phone is required';
      else if (!PHONE_RE.test(form.gymPhone.trim())) e.gymPhone = 'Invalid phone number';
      if (!form.contactEmail.trim()) e.contactEmail = 'Contact email is required';
      else if (!EMAIL_RE.test(form.contactEmail.trim())) e.contactEmail = 'Enter a valid email';
      if (!form.website.trim()) e.website = 'Website is required';
      else if (!isHttpsUrl(form.website)) e.website = 'Use the full address, starting with https://';
      if (form.description.trim().length < 30) e.description = 'Describe your gym in at least 30 characters';
      return e;
    },
    3: () => {
      const e = {};
      if (equipment.length === 0) e.equipment = 'Add at least one piece of equipment';
      return e;
    },
    4: () => {
      const e = {};
      if (gymPhotos.length < GYM_LIMITS.minPhotos) e.gymPhotos = 'Add at least one photo of your gym';
      if (equipmentPhotos.length < GYM_LIMITS.minPhotos) e.equipmentPhotos = 'Add at least one photo of your equipment';
      return e;
    },
  };

  const next = () => {
    const e = validators[step]();
    setErrors(e);
    if (Object.keys(e).length) return;
    setServerError('');
    setServerErrors([]);
    setStep(step + 1);
    scrollCardTop();
  };

  const back = () => {
    setErrors({});
    setServerError('');
    setServerErrors([]);
    setStep(step - 1);
    scrollCardTop();
  };

  /* ── Submit ─────────────────────────────────────────────────────── */
  const handleSubmit = async () => {
    // Re-check every step so nothing slips through after editing from the review screen.
    for (const s of [1, 2, 3, 4]) {
      const e = validators[s]();
      if (Object.keys(e).length) {
        setErrors(e);
        setStep(s);
        return;
      }
    }

    setServerError('');
    setServerErrors([]);
    setLoading(true);

    const data = new FormData();
    const text = {
      firstName: form.firstName, lastName: form.lastName, email: form.email.trim(), phone: form.phone,
      password: form.password, gymName: form.gymName, ownerRole: form.ownerRole, description: form.description,
      address: form.address, city: form.city, gymPhone: form.gymPhone, contactEmail: form.contactEmail,
      website: form.website, openingHours: form.openingHours,
    };
    Object.entries(text).forEach(([k, v]) => data.append(k, (v ?? '').toString().trim()));
    equipment.forEach((v) => data.append('equipment', v));
    classes.forEach((v) => data.append('classes', v));
    gymPhotos.forEach((p) => data.append('gymPhotos', p.file));
    equipmentPhotos.forEach((p) => data.append('equipmentPhotos', p.file));
    if (license) data.append('license', license);

    try {
      const result = await registerGymOwner(data);
      if (result.emailVerificationRequired === false) {
        setDone('resubmitted');
      } else {
        setStep(6);
        scrollCardTop();
      }
    } catch (err) {
      setServerError(err.message);
      setServerErrors(err.errors || []);
      scrollCardTop();
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (ev) => {
    ev.preventDefault();
    if (!/^\d{6}$/.test(form.otp)) {
      setErrors({ otp: 'Enter the 6-digit code from your email' });
      return;
    }
    setServerError('');
    setNotice('');
    setLoading(true);
    try {
      const response = await verifyEmail({ email: form.email.trim(), otp: form.otp });
      if (response.accessToken) {
        // Already approved by an admin before the owner verified their email.
        sessionStorage.setItem('vitrofitAuth', JSON.stringify({
          accessToken: response.accessToken, refreshToken: response.refreshToken, user: response.user,
        }));
        window.dispatchEvent(new Event('vitrofit-auth-change'));
        navigate('/');
        return;
      }
      setDone('pending');
    } catch (err) {
      setServerError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setServerError('');
    setNotice('');
    setLoading(true);
    try {
      await resendVerification({ email: form.email.trim() });
      setNotice('A new verification code has been sent to your email.');
    } catch (err) {
      setServerError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /* ── Small render helpers ───────────────────────────────────────── */
  const field = (id, label, { type = 'text', placeholder = '', max, required = true, hint } = {}) => (
    <div className={`rg-field ${errors[id] ? 'rg-field--error' : ''}`}>
      <label htmlFor={`rg-${id}`} className="rg-label">{label}{required && <span className="rg-req"> *</span>}</label>
      <input
        id={`rg-${id}`}
        type={type}
        className="rg-input"
        value={form[id]}
        placeholder={placeholder}
        maxLength={max}
        onChange={set(id)}
        aria-invalid={!!errors[id]}
        autoComplete={{ email: 'email', phone: 'tel', firstName: 'given-name', lastName: 'family-name' }[id] || 'off'}
      />
      {hint && !errors[id] && <span className="rg-hint">{hint}</span>}
      {errors[id] && <span className="auth-error">{errors[id]}</span>}
    </div>
  );

  const renderReview = (title, goTo, children) => (
    <section className="rg-review-block" key={title}>
      <header>
        <h3>{title}</h3>
        <button type="button" className="rg-edit" onClick={() => { setErrors({}); setStep(goTo); }}>Edit</button>
      </header>
      {children}
    </section>
  );

  const stepNumber = done ? STEPS.length : step;

  return (
    <main className="auth-page auth-page--register rg-page">
      <div className="auth-bg">
        <div className="auth-grid" />
        <div className="auth-glow auth-glow-1" />
        <div className="auth-glow auth-glow-2" />
      </div>

      <div className="auth-wrapper rg-wrapper">
        {/* ── Left: pitch + how it works ───────────────────────── */}
        <aside className="auth-brand rg-brand">
          <Link to="/" className="auth-logo">
            <div className="auth-logo-icon">V</div>
            <span className="auth-logo-text">Vitro<span>Fit</span></span>
          </Link>

          <div className="rg-brand-body">
            <p className="section-label">For gym owners</p>
            <h1 className="auth-headline">
              GROW YOUR<br /><span className="accent">GYM</span> WITH<br />VITROFIT
            </h1>
            <p className="rg-pitch">
              List your gym where active people search for a place to train. Verified gyms are
              highlighted on the map and in search.
            </p>

            <ul className="rg-perks">
              <li>Get discovered by members searching nearby</li>
              <li>Earn a Verified badge on your listing</li>
              <li>Keep your equipment and classes up to date</li>
            </ul>

            <section id="how-it-works" className="rg-how">
              <h2>How it works</h2>
              <ol>
                {HOW_IT_WORKS.map(([title, text], i) => (
                  <li key={title}>
                    <span className="rg-how-num">{i + 1}</span>
                    <div><strong>{title}</strong><p>{text}</p></div>
                  </li>
                ))}
              </ol>
            </section>
          </div>

          <div className="auth-brand-footer">
            <p>Just want to train? <Link to="/register" className="auth-link">Create a member account →</Link></p>
          </div>
        </aside>

        {/* ── Right: wizard ────────────────────────────────────── */}
        <div className="auth-card-wrap fade-right">
          <div className="auth-card rg-card" ref={cardRef}>
            {reapply && !done && (
              <div className="rg-banner" role="status">
                <strong>Re-applying.</strong> Sign in details are kept. Enter your email and password, update your
                gym details and we will review it again.
              </div>
            )}

            {!done && (
              <ol className="rg-steps" aria-label="Progress">
                {STEPS.map((label, i) => {
                  const n = i + 1;
                  const state = n < step ? 'done' : n === step ? 'active' : '';
                  return (
                    <li key={label} className={`rg-step ${state}`} aria-current={n === step ? 'step' : undefined}>
                      <span className="rg-step-dot">{n < step ? '✓' : n}</span>
                      <span className="rg-step-label">{label}</span>
                    </li>
                  );
                })}
              </ol>
            )}

            {(serverError || serverErrors.length > 0) && !done && (
              <div className="rg-alert" role="alert">
                <strong>{serverError || 'Please fix the following:'}</strong>
                {serverErrors.length > 1 && (
                  <ul>{serverErrors.map((m) => <li key={m}>{m}</li>)}</ul>
                )}
              </div>
            )}

            {/* ── 1. Account ── */}
            {!done && step === 1 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">{reapply ? 'Confirm Account' : 'Your Account'}</h2>
                  <p className="auth-card-sub">{reapply ? 'Use the email and password you registered with.' : 'You will use this to sign in once approved.'}</p>
                </div>
                <div className="rg-form">
                  {!reapply && (
                    <div className="rg-row">
                      {field('firstName', 'First name', { max: 100 })}
                      {field('lastName', 'Last name', { max: 100 })}
                    </div>
                  )}
                  {field('email', 'Email', { type: 'email', placeholder: 'you@yourgym.com', max: 200 })}
                  {!reapply && field('phone', 'Your phone', { type: 'tel', placeholder: '+94 77 123 4567', max: 20 })}

                  <div className={`rg-field ${errors.password ? 'rg-field--error' : ''}`}>
                    <label htmlFor="rg-password" className="rg-label">Password<span className="rg-req"> *</span></label>
                    <div className="rg-pw">
                      <input
                        id="rg-password"
                        type={showPw ? 'text' : 'password'}
                        className="rg-input"
                        value={form.password}
                        placeholder="At least 8 characters"
                        onChange={set('password')}
                        autoComplete={reapply ? 'current-password' : 'new-password'}
                        aria-invalid={!!errors.password}
                      />
                      <button type="button" className="rg-pw-toggle" onClick={() => setShowPw((v) => !v)}>
                        {showPw ? 'Hide' : 'Show'}
                      </button>
                    </div>
                    {errors.password && <span className="auth-error">{errors.password}</span>}
                  </div>

                  {!reapply && (
                    <>
                      <div className={`rg-field ${errors.confirm ? 'rg-field--error' : ''}`}>
                        <label htmlFor="rg-confirm" className="rg-label">Confirm password<span className="rg-req"> *</span></label>
                        <input
                          id="rg-confirm"
                          type={showPw ? 'text' : 'password'}
                          className="rg-input"
                          value={form.confirm}
                          onChange={set('confirm')}
                          autoComplete="new-password"
                          aria-invalid={!!errors.confirm}
                        />
                        {errors.confirm && <span className="auth-error">{errors.confirm}</span>}
                      </div>

                      <label className={`rg-check ${errors.terms ? 'rg-check--error' : ''}`}>
                        <input type="checkbox" checked={form.terms} onChange={set('terms')} />
                        <span>I confirm I am authorised to list this gym and agree to the VitroFit terms.</span>
                      </label>
                      {errors.terms && <span className="auth-error">{errors.terms}</span>}
                    </>
                  )}
                </div>
              </div>
            )}

            {/* ── 2. Gym details ── */}
            {!done && step === 2 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Your Gym</h2>
                  <p className="auth-card-sub">This is what our team reviews, so be accurate.</p>
                </div>
                <div className="rg-form">
                  {field('gymName', 'Gym name', { max: 150, placeholder: 'FitZone Colombo' })}

                  <div className="rg-field">
                    <span className="rg-label" id="rg-role-label">Your role at the gym<span className="rg-req"> *</span></span>
                    <div className="rg-choices" role="radiogroup" aria-labelledby="rg-role-label">
                      {['Owner', 'Manager'].map((r) => (
                        <label key={r} className={`rg-choice ${form.ownerRole === r ? 'selected' : ''}`}>
                          <input type="radio" name="ownerRole" value={r} checked={form.ownerRole === r} onChange={set('ownerRole')} />
                          {r}
                        </label>
                      ))}
                    </div>
                  </div>

                  {field('address', 'Street address', { max: 300, placeholder: '12 Galle Road' })}
                  <div className="rg-row">
                    {field('city', 'City', { max: 100, placeholder: 'Colombo' })}
                    {field('gymPhone', 'Gym phone', { type: 'tel', max: 20, placeholder: '011 234 5678' })}
                  </div>
                  <div className="rg-row">
                    {field('contactEmail', 'Public contact email', { type: 'email', max: 200, placeholder: 'hello@yourgym.com' })}
                    {field('website', 'Website', { type: 'url', max: 300, placeholder: 'https://yourgym.com', hint: 'We check this against your listing.' })}
                  </div>
                  {field('openingHours', 'Opening hours', { required: false, max: 300, placeholder: 'Mon-Fri 05:30-22:00, Sat-Sun 07:00-20:00' })}

                  <div className={`rg-field ${errors.description ? 'rg-field--error' : ''}`}>
                    <label htmlFor="rg-description" className="rg-label">
                      About your gym<span className="rg-req"> *</span>
                      <span className="rg-count">{form.description.trim().length}/1500</span>
                    </label>
                    <textarea
                      id="rg-description"
                      className="rg-input rg-textarea"
                      rows={4}
                      maxLength={1500}
                      value={form.description}
                      onChange={set('description')}
                      placeholder="Facilities, atmosphere, who it is for… (at least 30 characters)"
                      aria-invalid={!!errors.description}
                    />
                    {errors.description && <span className="auth-error">{errors.description}</span>}
                  </div>
                </div>
              </div>
            )}

            {/* ── 3. Equipment & classes ── */}
            {!done && step === 3 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Equipment &amp; Classes</h2>
                  <p className="auth-card-sub">Type an item and press Enter, or tap a suggestion.</p>
                </div>
                <div className="rg-form">
                  <TagInput
                    id="rg-equipment" label="Equipment" required hint="e.g. Treadmill"
                    tags={equipment} onChange={(t) => { setEquipment(t); setErrors((er) => ({ ...er, equipment: undefined })); }}
                    suggestions={EQUIPMENT_SUGGESTIONS} max={GYM_LIMITS.maxEquipment} error={errors.equipment}
                  />
                  <TagInput
                    id="rg-classes" label="Classes offered" hint="e.g. Yoga (optional)"
                    tags={classes} onChange={setClasses}
                    suggestions={CLASS_SUGGESTIONS} max={GYM_LIMITS.maxClasses}
                  />
                </div>
              </div>
            )}

            {/* ── 4. Photos & licence ── */}
            {!done && step === 4 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Photos &amp; Proof</h2>
                  <p className="auth-card-sub">Real photos help us approve you faster.</p>
                </div>
                <div className="rg-form">
                  <PhotoZone
                    id="rg-gym-photos" title="Gym photos" help="Entrance, floor, studios. JPG, PNG or WebP, up to 5 MB each."
                    photos={gymPhotos} onAdd={(f) => addPhotos('gym', f)} onRemove={(id) => removePhoto('gym', id)}
                    error={errors.gymPhotos}
                  />
                  <PhotoZone
                    id="rg-equipment-photos" title="Equipment photos" help="Show the machines and weights you listed. Up to 5 MB each."
                    photos={equipmentPhotos} onAdd={(f) => addPhotos('equipment', f)} onRemove={(id) => removePhoto('equipment', id)}
                    error={errors.equipmentPhotos}
                  />

                  <div className={`rg-field ${errors.license ? 'rg-field--error' : ''}`}>
                    <span className="rg-label">Business licence <em>(optional)</em></span>
                    {license ? (
                      <div className="rg-file">
                        <span className="rg-file-name">{license.name}</span>
                        <span className="rg-file-size">{formatBytes(license.size)}</span>
                        <button type="button" className="rg-edit" onClick={() => setLicense(null)}>Remove</button>
                      </div>
                    ) : (
                      <button type="button" className="rg-licence-btn" onClick={() => licenseRef.current?.click()}>
                        Upload registration or licence (PDF, JPG or PNG, up to 5 MB)
                      </button>
                    )}
                    <input
                      ref={licenseRef}
                      type="file"
                      hidden
                      accept={GYM_LIMITS.licenseTypes.join(',')}
                      onChange={(e) => { pickLicense(e.target.files?.[0]); e.target.value = ''; }}
                    />
                    <span className="rg-hint">Only our admins can open this document.</span>
                    {errors.license && <span className="auth-error">{errors.license}</span>}
                  </div>
                </div>
              </div>
            )}

            {/* ── 5. Review ── */}
            {!done && step === 5 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Review &amp; Submit</h2>
                  <p className="auth-card-sub">Check everything, then send it for approval.</p>
                </div>
                <div className="rg-form">
                  {renderReview("Account", 1, (
                    <dl>
                      {!reapply && <><dt>Name</dt><dd>{form.firstName} {form.lastName}</dd></>}
                      <dt>Email</dt><dd>{form.email}</dd>
                      {!reapply && <><dt>Phone</dt><dd>{form.phone}</dd></>}
                    </dl>
                  ))}
                  {renderReview("Gym", 2, (
                    <dl>
                      <dt>Name</dt><dd>{form.gymName} <span className="rg-pill">{form.ownerRole}</span></dd>
                      <dt>Address</dt><dd>{form.address}, {form.city}</dd>
                      <dt>Phone</dt><dd>{form.gymPhone}</dd>
                      <dt>Email</dt><dd>{form.contactEmail}</dd>
                      <dt>Website</dt><dd>{form.website}</dd>
                      {form.openingHours && <><dt>Hours</dt><dd>{form.openingHours}</dd></>}
                      <dt>About</dt><dd className="rg-about">{form.description}</dd>
                    </dl>
                  ))}
                  {renderReview("Equipment & classes", 3, (
                    <>
                      <div className="rg-chips">{equipment.map((t) => <span key={t}>{t}</span>)}</div>
                      {classes.length > 0 && <div className="rg-chips rg-chips--alt">{classes.map((t) => <span key={t}>{t}</span>)}</div>}
                    </>
                  ))}
                  {renderReview("Photos & licence", 4, (
                    <>
                      <ul className="rg-thumbs rg-thumbs--small">
                        {[...gymPhotos, ...equipmentPhotos].map((p) => <li key={p.id}><img src={p.url} alt={p.file.name} /></li>)}
                      </ul>
                      <p className="rg-hint">{license ? `Licence: ${license.name}` : 'No licence document attached.'}</p>
                    </>
                  ))}
                </div>
              </div>
            )}

            {/* ── 6. Verify email ── */}
            {!done && step === 6 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Verify Email</h2>
                  <p className="auth-card-sub">
                    We sent a 6-digit code to <strong>{form.email}</strong>. Enter it to submit your application.
                  </p>
                </div>
                <form className="rg-form" onSubmit={handleVerify} noValidate>
                  <div className={`rg-field ${errors.otp ? 'rg-field--error' : ''}`}>
                    <label htmlFor="rg-otp" className="rg-label">Verification code</label>
                    <input
                      id="rg-otp"
                      className="rg-input rg-otp"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      maxLength={6}
                      value={form.otp}
                      placeholder="123456"
                      onChange={(e) => { setForm((f) => ({ ...f, otp: e.target.value.replace(/\D/g, '') })); setErrors({}); }}
                    />
                    {errors.otp && <span className="auth-error">{errors.otp}</span>}
                  </div>
                  <button type="submit" className={`btn-primary auth-submit ${loading ? 'loading' : ''}`} disabled={loading || form.otp.length < 6}>
                    {loading ? <span className="auth-spinner" /> : <>Verify &amp; submit <span className="btn-arrow">→</span></>}
                  </button>
                  <p className="rg-resend">
                    Did not get it?{' '}
                    <button type="button" className="auth-link rg-link-btn" onClick={handleResend} disabled={loading}>Resend code</button>
                  </p>
                  {notice && <div className="rg-notice" role="status">{notice}</div>}
                </form>
              </div>
            )}

            {/* ── Done ── */}
            {done && (
              <div className="auth-step-panel rg-done">
                <div className="rg-done-icon" aria-hidden="true">✓</div>
                <h2 className="auth-card-title">{done === 'resubmitted' ? 'Application Re-submitted' : 'Application Received'}</h2>
                <p className="auth-card-sub">
                  {done === 'resubmitted'
                    ? 'Thanks for updating your details. We will review them again.'
                    : 'Your email is verified and your gym is now in our review queue.'}
                </p>
                <ol className="rg-timeline">
                  <li className="done"><strong>Application submitted</strong><span>{form.gymName || 'Your gym'}</span></li>
                  <li className="done"><strong>Email {done === 'resubmitted' ? 'on file' : 'verified'}</strong><span>{form.email}</span></li>
                  <li className="current"><strong>Admin review</strong><span>We will email you with the decision.</span></li>
                  <li><strong>Sign in &amp; go live</strong><span>Available once approved.</span></li>
                </ol>
                <div className="rg-done-actions">
                  <Link to="/" className="btn-primary">Back to home</Link>
                  <Link to="/login" className="btn-secondary">Sign in</Link>
                </div>
              </div>
            )}

            {/* ── Navigation buttons ── */}
            {!done && step < 6 && (
              <div className="rg-nav">
                {step > 1 && (
                  <button type="button" className="btn-secondary rg-back" onClick={back} disabled={loading}>← Back</button>
                )}
                {step < 5 ? (
                  <button type="button" className="btn-primary rg-next" onClick={next}>
                    Continue <span className="btn-arrow">→</span>
                  </button>
                ) : (
                  <button type="button" className={`btn-primary rg-next ${loading ? 'loading' : ''}`} onClick={handleSubmit} disabled={loading}>
                    {loading ? <span className="auth-spinner" /> : <>Submit application <span className="btn-arrow">→</span></>}
                  </button>
                )}
              </div>
            )}

            {!done && (
              <p className="auth-card-switch">
                Already approved? <Link to="/login" className="auth-link">Sign in →</Link>
                <span className="rg-progress-text"> · Step {stepNumber} of {STEPS.length}</span>
              </p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
