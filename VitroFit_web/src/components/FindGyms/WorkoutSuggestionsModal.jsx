import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { fetchGymWorkouts } from '../../api/gyms';
import './WorkoutSuggestionsModal.css';

const IconDumbbell = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 4v16M18 4v16M4 9h4M16 9h4M4 15h4M16 15h4M8 4h8M8 20h8"/>
  </svg>
);
const IconClose = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconClock = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
  </svg>
);

export default function WorkoutSuggestionsModal({ isOpen, onClose, gymName, place, cachedResult, onResult }) {
  const [entered, setEntered] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [workouts, setWorkouts] = useState([]);
  const [notes, setNotes] = useState('');
  const overlayRef = useRef(null);
  const requestRef = useRef(0);

  /* Animate in */
  useEffect(() => {
    if (isOpen) {
      const t = setTimeout(() => setEntered(true), 10);
      return () => clearTimeout(t);
    } else {
      setEntered(false);
    }
  }, [isOpen]);

  /* Fetch on open (unless a cached result was already handed to us), reset on close */
  useEffect(() => {
    if (!isOpen || !place) {
      setLoading(false);
      setError('');
      setWorkouts([]);
      setNotes('');
      return;
    }

    if (cachedResult) {
      setLoading(false);
      setError('');
      setWorkouts(cachedResult.workouts || []);
      setNotes(cachedResult.notes || '');
      return;
    }

    const requestId = ++requestRef.current;
    setLoading(true);
    setError('');
    setWorkouts([]);
    setNotes('');

    fetchGymWorkouts(place)
      .then((data) => {
        if (requestId !== requestRef.current) return;
        setWorkouts(data.workouts || []);
        setNotes(data.notes || '');
        setLoading(false);
        onResult?.(place.placeId, data);
      })
      .catch((err) => {
        if (requestId !== requestRef.current) return;
        setError(err.message || 'Could not load workout suggestions.');
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, place?.placeId, cachedResult]);

  /* Close on backdrop */
  const handleOverlayClick = (e) => {
    if (e.target === overlayRef.current) onClose();
  };

  /* Escape key */
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      ref={overlayRef}
      className={`wsm-overlay ${entered ? 'wsm-overlay--in' : ''}`}
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-label="Possible workouts"
    >
      <div className={`wsm-modal ${entered ? 'wsm-modal--in' : ''}`}>

        <div className="wsm-header">
          <div className="wsm-header-icon"><IconDumbbell /></div>
          <div>
            <h2 className="wsm-title">Possible Workouts</h2>
            <p className="wsm-subtitle">{gymName ? `AI-suggested for ${gymName}` : 'AI-suggested workouts'}</p>
          </div>
          <button className="wsm-close" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>

        <div className="wsm-body">
          {loading && (
            <div className="wsm-loading">
              <div className="wsm-progress"><div className="wsm-progress-bar" /></div>
              <span className="wsm-loading-label">Asking the fitness agent&hellip;</span>
            </div>
          )}

          {!loading && error && (
            <div className="wsm-error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {error}
            </div>
          )}

          {!loading && !error && workouts.length === 0 && (
            <div className="wsm-empty">No workout suggestions available for this gym yet.</div>
          )}

          {!loading && !error && workouts.length > 0 && (
            <div className="wsm-list">
              {workouts.map((w, i) => (
                <div className="wsm-card" key={`${w.name}-${i}`}>
                  <div className="wsm-card-header">
                    <span className="wsm-card-name">{w.name}</span>
                    <span className="wsm-card-duration"><IconClock />{w.duration_minutes} min</span>
                  </div>
                  <div className="wsm-card-chips">
                    {w.category && <span className="wsm-chip wsm-chip--category">{w.category}</span>}
                    {w.difficulty && <span className="wsm-chip wsm-chip--difficulty">{w.difficulty}</span>}
                  </div>
                  <p className="wsm-card-desc">{w.description}</p>
                  {w.equipment_used?.length > 0 && (
                    <div className="wsm-card-tags">
                      {w.equipment_used.map((item) => <span className="wsm-tag" key={item}>{item}</span>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {!loading && !error && notes && (
            <div className="wsm-notes">{notes}</div>
          )}
        </div>

        <div className="wsm-footer">
          <button className="wsm-close-btn" onClick={onClose}>Close</button>
        </div>

      </div>
    </div>,
    document.body
  );
}
