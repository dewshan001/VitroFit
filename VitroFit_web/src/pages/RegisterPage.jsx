import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './AuthPages.css';
import { register, verifyEmail, resendVerification } from '../api/auth';

export default function RegisterPage() {
  const [form, setForm] = useState({
    firstName: '', lastName: '', email: '', phone: '',
    password: '', confirm: '', terms: false, otp: ''
  });
  const [showPw, setShowPw]     = useState({ pw: false, conf: false });
  const [errors, setErrors]     = useState({});
  const [serverError, setServerError] = useState('');
  const [focused, setFocused]   = useState({});
  const [loading, setLoading]   = useState(false);
  const [step, setStep]         = useState(1); // 1 = personal info, 2 = plan & password, 3 = verify email
  const cardRef                 = useRef(null);
  const navigate                = useNavigate();

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    setTimeout(() => el.classList.add('visible'), 80);
  }, []);

  /* Mouse parallax tilt */
  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;
    const handleMove = (e) => {
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / rect.width * 5;
      const dy = (e.clientY - cy) / rect.height * 5;
      card.style.transform = `perspective(1200px) rotateY(${dx}deg) rotateX(${-dy}deg) translateY(0)`;
    };
    const handleLeave = () => {
      card.style.transform = 'perspective(1200px) rotateY(0deg) rotateX(0deg) translateY(0)';
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
    if (!form.firstName.trim())                        e.firstName = 'First name required';
    if (!form.lastName.trim())                         e.lastName  = 'Last name required';
    if (!form.email)                                   e.email     = 'Email is required';
    if (!form.phone)                                   e.phone     = 'Phone Number is required';
    else if (!/\S+@\S+\.\S+/.test(form.email))        e.email     = 'Enter a valid email';
    if (form.phone && !/^\+?[\d\s\-()]{7,15}$/.test(form.phone)) e.phone = 'Invalid phone number';
    return e;
  };

  const validateStep2 = () => {
    const e = {};
    if (!form.password)              e.password = 'Password is required';
    else if (form.password.length < 8) e.password = 'Minimum 8 characters';
    if (!form.confirm)               e.confirm  = 'Please confirm your password';
    else if (form.confirm !== form.password) e.confirm = 'Passwords do not match';
    if (!form.terms)                 e.terms    = 'You must accept the terms';
    return e;
  };

  const handleNext = () => {
    const e = validateStep1();
    setErrors(e);
    if (!Object.keys(e).length) setStep(2);
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    const e = validateStep2();
    setErrors(e);
    if (Object.keys(e).length) return;

    setServerError('');
    setLoading(true);

    try {
      await register({
        firstName: form.firstName,
        lastName: form.lastName,
        email: form.email,
        phone: form.phone,
        password: form.password,
      });

      // Move to email verification step
      setStep(3);
    } catch (error) {
      setServerError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (ev) => {
    ev.preventDefault();
    if (!form.otp || form.otp.length < 6) {
      setErrors({ otp: 'Please enter a valid 6-digit code' });
      return;
    }

    setServerError('');
    setLoading(true);

    try {
      const response = await verifyEmail({ email: form.email, otp: form.otp });
      
      const authState = {
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
        user: response.user,
      };
      sessionStorage.setItem('vitrofitAuth', JSON.stringify(authState));
      navigate('/');
    } catch (error) {
      setServerError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setServerError('');
    setLoading(true);
    try {
      await resendVerification({ email: form.email });
      setServerError('A new verification code has been sent to your email.');
    } catch (error) {
      setServerError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, val) => {
    setForm(f => ({ ...f, [field]: val }));
    if (errors[field]) setErrors(e => ({ ...e, [field]: '' }));
    if (serverError && serverError !== 'A new verification code has been sent to your email.') setServerError('');
  };

  const passwordStrength = () => {
    const pw = form.password;
    if (!pw) return 0;
    let s = 0;
    if (pw.length >= 8) s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return s;
  };
  const strength = passwordStrength();
  const strengthLabels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const strengthColors = ['', '#ff4d4d', '#ffa500', '#c8f000', '#00ff88'];

  const field = (id, label, type = 'text', placeholder = '', maxLength) => (
    <div className={`auth-field ${focused[id] ? 'auth-field--focused' : ''} ${errors[id] ? 'auth-field--error' : ''} ${form[id] ? 'auth-field--filled' : ''}`}>
      <label htmlFor={`reg-${id}`} className="auth-label">{label}</label>
      <div className="auth-input-wrap">
        <input
          id={`reg-${id}`}
          type={type}
          className="auth-input"
          value={form[id]}
          onChange={e => handleChange(id, e.target.value)}
          onFocus={() => setFocused(f => ({ ...f, [id]: true }))}
          onBlur={() => setFocused(f => ({ ...f, [id]: false }))}
          placeholder={placeholder}
          maxLength={maxLength}
        />
      </div>
      {errors[id] && <span className="auth-error">{errors[id]}</span>}
    </div>
  );

  return (
    <main className="auth-page auth-page--register">
      {/* Background */}
      <div className="auth-bg">
        <div className="auth-grid" />
        <div className="auth-glow auth-glow-1" />
        <div className="auth-glow auth-glow-2" />
      </div>

      <div className="auth-wrapper auth-wrapper--register">
        {/* Left branding panel */}
        <div className="auth-brand fade-left visible">
          <Link to="/" className="auth-logo">
            <div className="auth-logo-icon">V</div>
            <span className="auth-logo-text">Vitro<span>Fit</span></span>
          </Link>

          <div className="auth-brand-body">
            <p className="section-label">Join the community</p>
            <h1 className="auth-headline">
              START YOUR<br /><span className="accent">JOURNEY</span><br />TODAY
            </h1>
            <p className="auth-sub">
              Join thousands of members who have already transformed their
              fitness journey with VitroFit's expert coaching.
            </p>

            <div className="auth-stats">
              {[['5K+', 'Active Members'], ['120+', 'Weekly Classes'], ['98%', 'Satisfaction']].map(([n, l]) => (
                <div key={l} className="auth-stat">
                  <span className="auth-stat-num">{n}</span>
                  <span className="auth-stat-label">{l}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="auth-brand-footer">
            <p>Already a member? <Link to="/login" className="auth-link">Sign in →</Link></p>
          </div>
        </div>

        {/* Right card */}
        <div className="auth-card-wrap fade-right visible">
          <div className="auth-card auth-card--register" ref={cardRef}>
            {/* Step indicator */}
            <div className="auth-steps">
              <div className={`auth-step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'done' : ''}`}>
                <div className="auth-step-dot">{step > 1 ? '✓' : '1'}</div>
                <span>Personal</span>
              </div>
              <div className="auth-step-line" />
              <div className={`auth-step ${step >= 2 ? 'active' : ''} ${step > 2 ? 'done' : ''}`}>
                <div className="auth-step-dot">{step > 2 ? '✓' : '2'}</div>
                <span>Security</span>
              </div>
              <div className="auth-step-line" />
              <div className={`auth-step ${step >= 3 ? 'active' : ''}`}>
                <div className="auth-step-dot">3</div>
                <span>Verify</span>
              </div>
            </div>

            {step === 1 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Create Account</h2>
                  <p className="auth-card-sub">Tell us about yourself</p>
                </div>

                <div className="auth-form">
                  <div className="auth-row">
                    {field('firstName', 'First Name', 'text', 'Sadeepa')}
                    {field('lastName', 'Last Name', 'text', 'Godage')}
                  </div>
                  {field('email', 'Email Address', 'email', 'sadeepa.godage@gmail.com')}
                  {field('phone', 'Phone', 'tel', '+94 77 123 4567')}

                  <button id="reg-next" type="button" className="btn-primary auth-submit" onClick={handleNext}>
                    Continue <span className="btn-arrow">→</span>
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Secure Account</h2>
                  <p className="auth-card-sub">Create a strong password</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit} noValidate>
                  {/* Password */}
                  <div className={`auth-field ${focused.password ? 'auth-field--focused' : ''} ${errors.password ? 'auth-field--error' : ''} ${form.password ? 'auth-field--filled' : ''}`}>
                    <label htmlFor="reg-password" className="auth-label">Password</label>
                    <div className="auth-input-wrap">
                      <svg className="auth-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                      <input
                        id="reg-password"
                        type={showPw.pw ? 'text' : 'password'}
                        className="auth-input"
                        value={form.password}
                        onChange={e => handleChange('password', e.target.value)}
                        onFocus={() => setFocused(f => ({ ...f, password: true }))}
                        onBlur={() => setFocused(f => ({ ...f, password: false }))}
                        placeholder="Min. 8 characters"
                      />
                      <button type="button" className="auth-toggle-pw" onClick={() => setShowPw(s => ({ ...s, pw: !s.pw }))}>
                        {showPw.pw
                          ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                          : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        }
                      </button>
                    </div>
                    {form.password && (
                      <div className="auth-strength">
                        <div className="auth-strength-bars">
                          {[1, 2, 3, 4].map(i => (
                            <div
                              key={i}
                              className="auth-strength-bar"
                              style={{ background: i <= strength ? strengthColors[strength] : 'rgba(255,255,255,0.1)' }}
                            />
                          ))}
                        </div>
                        <span style={{ color: strengthColors[strength] }}>{strengthLabels[strength]}</span>
                      </div>
                    )}
                    {errors.password && <span className="auth-error">{errors.password}</span>}
                  </div>

                  {/* Confirm */}
                  <div className={`auth-field ${focused.confirm ? 'auth-field--focused' : ''} ${errors.confirm ? 'auth-field--error' : ''} ${form.confirm ? 'auth-field--filled' : ''}`}>
                    <label htmlFor="reg-confirm" className="auth-label">Confirm Password</label>
                    <div className="auth-input-wrap">
                      <svg className="auth-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                      <input
                        id="reg-confirm"
                        type={showPw.conf ? 'text' : 'password'}
                        className="auth-input"
                        value={form.confirm}
                        onChange={e => handleChange('confirm', e.target.value)}
                        onFocus={() => setFocused(f => ({ ...f, confirm: true }))}
                        onBlur={() => setFocused(f => ({ ...f, confirm: false }))}
                        placeholder="Re-enter password"
                      />
                      <button type="button" className="auth-toggle-pw" onClick={() => setShowPw(s => ({ ...s, conf: !s.conf }))}>
                        {showPw.conf
                          ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                          : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        }
                      </button>
                    </div>
                    {errors.confirm && <span className="auth-error">{errors.confirm}</span>}
                  </div>

                  {/* Terms */}
                  <div className={`auth-terms-wrap ${errors.terms ? 'auth-field--error' : ''}`}>
                    <label className="auth-remember">
                      <input
                        type="checkbox"
                        id="reg-terms"
                        className="auth-check"
                        checked={form.terms}
                        onChange={e => handleChange('terms', e.target.checked)}
                      />
                      <span className="auth-checkmark" />
                      I agree to the <Link to="/terms" className="auth-link">Terms of Service</Link> & <Link to="/privacy" className="auth-link">Privacy Policy</Link>
                    </label>
                    {errors.terms && <span className="auth-error">{errors.terms}</span>}
                  </div>

                  <div className="auth-step-btns">
                    <button type="button" className="btn-secondary auth-back" onClick={() => setStep(1)}>
                      ← Back
                    </button>
                    <button id="reg-submit" type="submit" className={`btn-primary auth-submit auth-submit--flex ${loading ? 'loading' : ''}`} disabled={loading}>
                      {loading
                        ? <span className="auth-spinner" />
                        : <>Create Account <span className="btn-arrow">→</span></>
                      }
                    </button>
                  </div>

                  {serverError && <div className="auth-server-error">{serverError}</div>}
                </form>
              </div>
            )}

            {step === 3 && (
              <div className="auth-step-panel">
                <div className="auth-card-header">
                  <h2 className="auth-card-title">Verify Email</h2>
                  <p className="auth-card-sub">
                    We sent a 6-digit code to <strong>{form.email}</strong>. 
                    Please enter it below to activate your account.
                  </p>
                </div>

                <form className="auth-form" onSubmit={handleVerifyOTP} noValidate>
                  {field('otp', 'Verification Code', 'text', '123456', 6)}

                  <button type="submit" className={`btn-primary auth-submit auth-submit--flex ${loading ? 'loading' : ''}`} disabled={loading || !form.otp}>
                    {loading
                      ? <span className="auth-spinner" />
                      : <>Verify & Login <span className="btn-arrow">→</span></>
                    }
                  </button>

                  <div className="auth-resend-wrap" style={{ marginTop: '20px', textAlign: 'center' }}>
                    <p style={{ color: '#9ca3af', fontSize: '14px' }}>
                      Didn't receive the email? <button type="button" onClick={handleResendOTP} className="auth-link" disabled={loading} style={{ background: 'none', border: 'none', padding: 0, font: 'inherit', cursor: 'pointer' }}>Resend Code</button>
                    </p>
                  </div>

                  {serverError && (
                    <div className="auth-server-error" style={serverError.includes('sent') ? { backgroundColor: 'rgba(0, 255, 136, 0.1)', color: '#00ff88', border: '1px solid rgba(0, 255, 136, 0.2)' } : {}}>
                      {serverError}
                    </div>
                  )}
                </form>
              </div>
            )}

            <p className="auth-card-switch">
              Already a member? <Link to="/login" className="auth-link">Sign in →</Link>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
