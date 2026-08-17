import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './AuthPages.css';
import { forgotPassword, resetPassword } from '../api/auth';

export default function ForgotPasswordPage() {
  const [step, setStep]           = useState(1); // 1 = Request OTP, 2 = Reset Password
  const [form, setForm]           = useState({ email: '', otp: '', newPassword: '' });
  const [showPw, setShowPw]       = useState(false);
  const [errors, setErrors]       = useState({});
  const [serverError, setServerError] = useState('');
  const [successMsg, setSuccessMsg]   = useState('');
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

  const validateStep1 = () => {
    const e = {};
    if (!form.email)                          e.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = 'Enter a valid email';
    return e;
  };

  const validateStep2 = () => {
    const e = {};
    if (!form.otp)                                e.otp = 'OTP is required';
    else if (form.otp.length !== 6)               e.otp = 'Must be 6 digits';
    if (!form.newPassword)                        e.newPassword = 'Password is required';
    else if (form.newPassword.length < 8)         e.newPassword = 'Minimum 8 characters';
    return e;
  };

  const handleRequestOTP = async (ev) => {
    ev.preventDefault();
    const e = validateStep1();
    setErrors(e);
    if (Object.keys(e).length) return;

    setServerError('');
    setSuccessMsg('');
    setLoading(true);

    try {
      const res = await forgotPassword(form.email);
      setSuccessMsg(res.message || 'OTP sent successfully.');
      setStep(2);
    } catch (error) {
      setServerError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (ev) => {
    ev.preventDefault();
    const e = validateStep2();
    setErrors(e);
    if (Object.keys(e).length) return;

    setServerError('');
    setSuccessMsg('');
    setLoading(true);

    try {
      const res = await resetPassword(form.email, form.otp, form.newPassword);
      setSuccessMsg(res.message || 'Password reset successfully.');
      setTimeout(() => navigate('/login'), 2000);
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
    if (successMsg) setSuccessMsg('');
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
            <p className="section-label">Account Recovery</p>
            <h1 className="auth-headline">
              GET BACK<br /><span className="accent">IN THE</span><br />GAME
            </h1>
            <p className="auth-sub">
              Forgot your password? No worries. Request a recovery code to reset it and jump straight back into your fitness journey.
            </p>
          </div>

          <div className="auth-brand-footer">
            <p>Remember your password? <Link to="/login" className="auth-link">Sign in here →</Link></p>
          </div>
        </div>

        {/* Right card */}
        <div className="auth-card-wrap fade-right visible">
          <div className="auth-card" ref={cardRef}>
            
            {step === 1 && (
              <>
                <div className="auth-card-header">
                  <p className="section-label">Step 1 of 2</p>
                  <h2 className="auth-card-title">Reset Password</h2>
                  <p className="auth-card-sub">Enter your email to receive a recovery code</p>
                </div>

                <form className="auth-form" onSubmit={handleRequestOTP} noValidate>
                  {/* Email */}
                  <div className={`auth-field ${focused.email ? 'auth-field--focused' : ''} ${errors.email ? 'auth-field--error' : ''} ${form.email ? 'auth-field--filled' : ''}`}>
                    <label htmlFor="reset-email" className="auth-label">Email address</label>
                    <div className="auth-input-wrap">
                      <svg className="auth-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                      <input
                        id="reset-email"
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

                  <button type="submit" className={`btn-primary auth-submit ${loading ? 'loading' : ''}`} disabled={loading}>
                    {loading
                      ? <span className="auth-spinner" />
                      : <>Send Recovery Code <span className="btn-arrow">→</span></>
                    }
                  </button>

                  {serverError && <div className="auth-server-error">{serverError}</div>}
                  {successMsg && <div style={{color: 'var(--accent)', fontSize: '0.85rem', marginTop: '10px'}}>{successMsg}</div>}
                </form>
              </>
            )}

            {step === 2 && (
              <>
                <div className="auth-card-header">
                  <p className="section-label">Step 2 of 2</p>
                  <h2 className="auth-card-title">Create New Password</h2>
                  <p className="auth-card-sub">Check {form.email} for the 6-digit recovery code</p>
                </div>

                <form className="auth-form" onSubmit={handleResetPassword} noValidate>
                  {/* OTP */}
                  <div className={`auth-field ${focused.otp ? 'auth-field--focused' : ''} ${errors.otp ? 'auth-field--error' : ''} ${form.otp ? 'auth-field--filled' : ''}`}>
                    <label htmlFor="reset-otp" className="auth-label">Recovery Code</label>
                    <div className="auth-input-wrap">
                      <svg className="auth-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                      <input
                        id="reset-otp"
                        type="text"
                        maxLength="6"
                        className="auth-input"
                        value={form.otp}
                        onChange={e => handleChange('otp', e.target.value.replace(/\D/g, ''))}
                        onFocus={() => setFocused(f => ({ ...f, otp: true }))}
                        onBlur={() => setFocused(f => ({ ...f, otp: false }))}
                        placeholder="123456"
                      />
                    </div>
                    {errors.otp && <span className="auth-error">{errors.otp}</span>}
                  </div>

                  {/* New Password */}
                  <div className={`auth-field ${focused.newPassword ? 'auth-field--focused' : ''} ${errors.newPassword ? 'auth-field--error' : ''} ${form.newPassword ? 'auth-field--filled' : ''}`}>
                    <label htmlFor="reset-new-password" className="auth-label">New Password</label>
                    <div className="auth-input-wrap">
                      <svg className="auth-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                      <input
                        id="reset-new-password"
                        type={showPw ? 'text' : 'password'}
                        className="auth-input"
                        value={form.newPassword}
                        onChange={e => handleChange('newPassword', e.target.value)}
                        onFocus={() => setFocused(f => ({ ...f, newPassword: true }))}
                        onBlur={() => setFocused(f => ({ ...f, newPassword: false }))}
                        placeholder="Min. 8 characters"
                      />
                      <button type="button" className="auth-toggle-pw" onClick={() => setShowPw(s => !s)} aria-label="Toggle password visibility">
                        {showPw
                          ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                          : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        }
                      </button>
                    </div>
                    {errors.newPassword && <span className="auth-error">{errors.newPassword}</span>}
                  </div>

                  <button type="submit" className={`btn-primary auth-submit ${loading ? 'loading' : ''}`} disabled={loading}>
                    {loading
                      ? <span className="auth-spinner" />
                      : <>Reset Password <span className="btn-arrow">→</span></>
                    }
                  </button>

                  <div style={{ marginTop: '16px', textAlign: 'center' }}>
                    <button type="button" className="auth-link" onClick={() => setStep(1)} style={{ background: 'none', border: 'none', fontSize: '0.85rem' }}>
                      ← Back to email
                    </button>
                  </div>

                  {serverError && <div className="auth-server-error">{serverError}</div>}
                  {successMsg && <div style={{color: 'var(--accent)', fontSize: '0.85rem', marginTop: '10px'}}>{successMsg}</div>}
                </form>
              </>
            )}

          </div>
        </div>
      </div>
    </main>
  );
}
