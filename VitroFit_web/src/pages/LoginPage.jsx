import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './AuthPages.css';
import { login } from '../api/auth';

export default function LoginPage() {
  const [form, setForm]           = useState({ email: '', password: '' });
  const [showPw, setShowPw]       = useState(false);
  const [errors, setErrors]       = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading]     = useState(false);
  const [focused, setFocused]     = useState({});
  const cardRef                   = useRef(null);
  const navigate                  = useNavigate();

  /* ── Scroll-reveal on mount ── */
  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    setTimeout(() => el.classList.add('visible'), 80);
  }, []);

  /* ── Mouse parallax tilt ── */
  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;
    const handleMove = (e) => {
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width  / 2;
      const cy = rect.top  + rect.height / 2;
      const dx = (e.clientX - cx) / rect.width  * 6;
      const dy = (e.clientY - cy) / rect.height * 6;
      card.style.transform = `perspective(1000px) rotateY(${dx}deg) rotateX(${-dy}deg) translateY(0)`;
    };
    const handleLeave = () => {
      card.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) translateY(0)';
    };
    card.addEventListener('mousemove', handleMove);
    card.addEventListener('mouseleave', handleLeave);
    return () => {
      card.removeEventListener('mousemove', handleMove);
      card.removeEventListener('mouseleave', handleLeave);
    };
  }, []);

  const validate = () => {
    const e = {};
    if (!form.email)                          e.email    = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email  = 'Enter a valid email';
    if (!form.password)                        e.password = 'Password is required';
    else if (form.password.length < 6)         e.password = 'Minimum 6 characters';
    return e;
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;

    setServerError('');
    setLoading(true);

    try {
      const response = await login({ email: form.email, password: form.password });
      const authState = {
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
        user: response.user,
      };
      localStorage.setItem('vitrofitAuth', JSON.stringify(authState));
      window.dispatchEvent(new Event('vitrofit-auth-change'));
      navigate('/');
    } catch (error) {
      setServerError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, val) => {
    setForm(f => ({ ...f, [field]: val }));
    if (errors[field]) setErrors(e => ({ ...e, [field]: '' }));
    if (serverError) setServerError('');
  };

  return (
    <main className="auth-page">
      {/* Animated background grid */}
      <div className="auth-bg">
        <div className="auth-grid" />
        <div className="auth-glow auth-glow-1" />
        <div className="auth-glow auth-glow-2" />
      </div>

      <div className="auth-wrapper">
        {/* Left branding panel */}
        <div className="auth-brand fade-left visible">
          <Link to="/" className="auth-logo">
            <div className="auth-logo-icon">V</div>
            <span className="auth-logo-text">Vitro<span>Fit</span></span>
          </Link>

          <div className="auth-brand-body">
            <p className="section-label">Welcome Back</p>
            <h1 className="auth-headline">
              PUSH YOUR<br /><span className="accent">LIMITS</span><br />DAILY
            </h1>
            <p className="auth-sub">
              Access your personalised training dashboard, track your progress,
              and stay ahead of the competition.
            </p>

            <ul className="auth-perks">
              {['Personalised workout plans', 'Live class timetable', 'Progress analytics'].map(p => (
                <li key={p}>
                  <span className="perk-dot" />
                  {p}
                </li>
              ))}
            </ul>
          </div>

          <div className="auth-brand-footer">
            <p>Don't have an account? <Link to="/register" className="auth-link">Sign up free →</Link></p>
          </div>
        </div>

        {/* Right card */}
        <div className="auth-card-wrap fade-right visible">
          <div className="auth-card" ref={cardRef}>
            <div className="auth-card-header">
              <p className="section-label">Member portal</p>
              <h2 className="auth-card-title">Sign In</h2>
              <p className="auth-card-sub">Enter your credentials to continue</p>
            </div>

            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              {/* Email */}
              <div className={`auth-field ${focused.email ? 'auth-field--focused' : ''} ${errors.email ? 'auth-field--error' : ''} ${form.email ? 'auth-field--filled' : ''}`}>
                <label htmlFor="login-email" className="auth-label">Email address</label>
                <div className="auth-input-wrap">
                  <svg className="auth-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                  <input
                    id="login-email"
                    type="email"
                    className="auth-input"
                    value={form.email}
                    onChange={e => handleChange('email', e.target.value)}
                    onFocus={() => setFocused(f => ({ ...f, email: true }))}
                    onBlur={() => setFocused(f => ({ ...f, email: false }))}
                    autoComplete="email"
                    placeholder="you@example.com"
                  />
                </div>
                {errors.email && <span className="auth-error">{errors.email}</span>}
              </div>

              {/* Password */}
              <div className={`auth-field ${focused.password ? 'auth-field--focused' : ''} ${errors.password ? 'auth-field--error' : ''} ${form.password ? 'auth-field--filled' : ''}`}>
                <label htmlFor="login-password" className="auth-label">Password</label>
                <div className="auth-input-wrap">
                  <svg className="auth-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                  <input
                    id="login-password"
                    type={showPw ? 'text' : 'password'}
                    className="auth-input"
                    value={form.password}
                    onChange={e => handleChange('password', e.target.value)}
                    onFocus={() => setFocused(f => ({ ...f, password: true }))}
                    onBlur={() => setFocused(f => ({ ...f, password: false }))}
                    autoComplete="current-password"
                    placeholder="••••••••"
                  />
                  <button type="button" className="auth-toggle-pw" onClick={() => setShowPw(s => !s)} aria-label="Toggle password visibility">
                    {showPw
                      ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                    }
                  </button>
                </div>
                {errors.password && <span className="auth-error">{errors.password}</span>}
              </div>

              <div className="auth-meta">
                <label className="auth-remember">
                  <input type="checkbox" className="auth-check" id="remember" />
                  <span className="auth-checkmark" />
                  Remember me
                </label>
                <Link to="/forgot-password" className="auth-link auth-forgot">Forgot password?</Link>
              </div>

              <button id="login-submit" type="submit" className={`btn-primary auth-submit ${loading ? 'loading' : ''}`} disabled={loading}>
                {loading
                  ? <span className="auth-spinner" />
                  : <>Sign In <span className="btn-arrow">→</span></>
                }
              </button>

              {serverError && <div className="auth-server-error">{serverError}</div>}

              <div className="auth-divider"><span>or continue with</span></div>

              <div className="auth-socials">
                <button type="button" id="login-google" className="auth-social-btn">
                  <svg viewBox="0 0 24 24"><path fill="#EA4335" d="M5.27 9.76A7.08 7.08 0 0112 4.9c1.76 0 3.35.65 4.58 1.7L19.9 3.3A12 12 0 000 12c0 1.99.49 3.87 1.36 5.52l3.91-3.04A7.07 7.07 0 015.27 9.76z"/><path fill="#FBBC05" d="M5.27 14.24A7.08 7.08 0 0012 19.1c1.74 0 3.32-.52 4.63-1.42L12.87 14A7.07 7.07 0 015.27 14.24z" /><path fill="#34A853" d="M19.1 12c0-.65-.06-1.28-.18-1.9H12v3.59h3.99A3.52 3.52 0 0116.63 14l3.76 2.92A11.97 11.97 0 0024 12h-4.9z" /><path fill="#4285F4" d="M12 24c3.24 0 5.95-1.07 7.94-2.91L16.18 18.1A7.17 7.17 0 0112 19.1a7.08 7.08 0 01-6.73-4.86l-3.91 3.04A12 12 0 0012 24z" /></svg>
                  Google
                </button>
                <button type="button" id="login-facebook" className="auth-social-btn">
                  <svg viewBox="0 0 24 24" fill="#1877F2"><path d="M24 12.073C24 5.4 18.627 0 12 0S0 5.4 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047V9.41c0-3.025 1.792-4.696 4.533-4.696 1.312 0 2.686.236 2.686.236v2.97h-1.513c-1.491 0-1.956.93-1.956 1.884v2.25h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>
                  Facebook
                </button>
              </div>
            </form>

            <p className="auth-card-switch">
              New to VitroFit? <Link to="/register" className="auth-link">Create account →</Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
