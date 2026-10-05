import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getTimetableReviews,
  getTimetableReview,
  approveTimetable,
  rejectTimetable,
} from '../api/timetableReviews';
import './TimetableReviewsPage.css';

const FILTERS = ['Pending', 'Approved', 'Rejected'];
const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const BADGE = { Pending: 'pending', Approved: 'approved', Rejected: 'rejected' };

const isReviewer = (role) => role === 2 || role === 3 || role === 'Admin' || role === 'Gym_Owner';

function formatDateTime(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

/** Weekly view of a proposed timetable: one column per day, sessions in time order. */
function WeekGrid({ slots }) {
  return (
    <div className="tr-week">
      {DAY_NAMES.map((name, i) => {
        const day = slots.filter((s) => s.day === i + 1).sort((a, b) => a.startTime.localeCompare(b.startTime));
        return (
          <div className={`tr-day ${day.length === 0 ? 'tr-day--rest' : ''}`} key={name}>
            <h4>{name.slice(0, 3)}<span>{name.slice(3)}</span></h4>
            {day.length === 0 ? (
              <p className="tr-rest">Rest</p>
            ) : (
              day.map((s, k) => (
                <div className="tr-slot" key={`${s.startTime}-${k}`}>
                  <span className="tr-slot-time">{s.startTime} – {s.endTime}</span>
                  <strong>{s.focus}</strong>
                  {s.description && (
                    <ul>
                      {s.description.split(',').map((part, n) => <li key={n}>{part.trim()}</li>)}
                    </ul>
                  )}
                </div>
              ))
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Shared queue where approved gym owners and admins verify members' AI-generated timetables. */
export default function TimetableReviewsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('Pending');
  const [rows, setRows] = useState([]);
  const [counts, setCounts] = useState({ pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [openId, setOpenId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState('');
  const [deciding, setDeciding] = useState(false);
  const [banner, setBanner] = useState(null); // { kind: 'ok' | 'warn', text }

  // Route guard: approved gym owners and admins only (the API enforces this too).
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem('vitrofitAuth');
      if (!stored) { navigate('/login'); return; }
      if (!isReviewer(JSON.parse(stored).user?.role)) navigate('/');
    } catch {
      navigate('/login');
    }
  }, [navigate]);

  const load = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true);
    setError('');
    try {
      const data = await getTimetableReviews(status);
      setRows(data?.items || []);
      setCounts(data?.counts || { pending: 0, approved: 0, rejected: 0 });
    } catch (err) {
      setError('Failed to load timetable requests: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => { load(); }, [load]);

  // New requests arrive while the page is open.
  useEffect(() => {
    if (status !== 'Pending') return undefined;
    const timer = setInterval(() => load({ quiet: true }), 30000);
    return () => clearInterval(timer);
  }, [status, load]);

  const open = async (row) => {
    setOpenId(row.id);
    setDetail(null);
    setDetailError('');
    setRejecting(false);
    setNote('');
    setBanner(null);
    setDetailLoading(true);
    try {
      setDetail(await getTimetableReview(row.id));
    } catch (err) {
      setDetailError(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const close = useCallback(() => {
    if (deciding) return;
    setOpenId(null);
    setDetail(null);
  }, [deciding]);

  useEffect(() => {
    if (!openId) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') close(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [openId, close]);

  const decide = async (approve) => {
    setDeciding(true);
    setDetailError('');
    try {
      const result = approve
        ? await approveTimetable(openId, note.trim())
        : await rejectTimetable(openId, note.trim());
      setBanner(result?.warning
        ? { kind: 'warn', text: result.warning }
        : { kind: 'ok', text: `Timetable ${approve ? 'verified' : 'rejected'}. The member has been notified.` });
      setOpenId(null);
      setDetail(null);
      load({ quiet: true });
    } catch (err) {
      // Someone else may have just decided it: refresh the list so it disappears.
      setDetailError(err.message);
      load({ quiet: true });
    } finally {
      setDeciding(false);
    }
  };

  const decided = detail && detail.status !== 'Pending';

  return (
    <main className="tr-page">
      <header className="tr-header">
        <div className="tr-header-inner">
          <h1 className="tr-title">Timetable <span>Reviews</span></h1>
          <p className="tr-sub">
            Members&apos; AI-generated weekly timetables wait here until a gym owner verifies them.
            The member keeps their current timetable until you approve.
          </p>
        </div>
      </header>

      <div className="tr-content">
        {banner && (
          <div className={`tr-banner tr-banner--${banner.kind}`} role="status">
            {banner.text}
            <button type="button" onClick={() => setBanner(null)} aria-label="Dismiss">×</button>
          </div>
        )}

        <div className="tr-filters" role="tablist" aria-label="Request status">
          {FILTERS.map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={status === f}
              className={`tr-filter ${status === f ? 'active' : ''}`}
              onClick={() => setStatus(f)}
            >
              {f}
              <span className={`tr-count ${f === 'Pending' && counts.pending > 0 ? 'hot' : ''}`}>{counts[f.toLowerCase()] ?? 0}</span>
            </button>
          ))}
        </div>

        <div className="tr-card">
          {loading ? (
            <div className="tr-muted">Loading...</div>
          ) : error ? (
            <div className="tr-muted tr-muted--error">{error}</div>
          ) : rows.length === 0 ? (
            <div className="tr-muted">
              {status === 'Pending' ? 'Nothing is waiting for verification. 🎉' : `No ${status.toLowerCase()} timetables yet.`}
            </div>
          ) : (
            <div className="tr-table-wrap">
              <table className="tr-table">
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Goal</th>
                    <th>Plan</th>
                    <th>{status === 'Pending' ? 'Submitted' : 'Reviewed'}</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.id}>
                      <td><strong>{r.memberName}</strong></td>
                      <td><span className="tr-goal">{r.goal || '-'}</span></td>
                      <td>{r.slotCount} sessions · {r.daysPerWeek} days/week · {r.sessionMinutes} min</td>
                      <td className="tr-date">
                        {status === 'Pending' ? formatDateTime(r.createdAt) : formatDateTime(r.reviewedAt)}
                        {status !== 'Pending' && r.reviewerName && <div>by {r.reviewerName}</div>}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button className="btn-primary" onClick={() => open(r)}>{status === 'Pending' ? 'Review' : 'View'}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {openId && (
        <div className="tr-overlay" onClick={close}>
          <div className="tr-modal" role="dialog" aria-modal="true" aria-label="Timetable review" onClick={(e) => e.stopPropagation()}>
            {detailLoading && <div className="tr-muted">Loading timetable...</div>}
            {!detailLoading && !detail && detailError && <div className="tr-muted tr-muted--error">{detailError}</div>}

            {detail && (
              <>
                <div className="tr-modal-head">
                  <div>
                    <h2>{detail.memberName}&apos;s timetable</h2>
                    <p>Submitted {formatDateTime(detail.createdAt)}</p>
                  </div>
                  <span className={`tr-badge tr-badge--${BADGE[detail.status] || ''}`}>{detail.status}</span>
                </div>

                <div className="tr-modal-body">
                  <dl className="tr-facts">
                    <dt>Goal</dt><dd>{detail.goal || '-'}</dd>
                    <dt>Availability</dt><dd>{detail.daysPerWeek} days a week, {detail.sessionMinutes} minutes a session</dd>
                    <dt>Equipment</dt>
                    <dd>
                      {detail.equipment.length === 0
                        ? <span className="tr-faint">None listed</span>
                        : <span className="tr-chips">{detail.equipment.map((e) => <span key={e}>{e.replace(/_/g, ' ')}</span>)}</span>}
                    </dd>
                    {detail.preferences && (<><dt>Preferences</dt><dd className="tr-pre">{detail.preferences}</dd></>)}
                  </dl>

                  <WeekGrid slots={detail.slots} />

                  {detail.longTermImpact && (
                    <div className="tr-impact">
                      <h4>Expected long-term impact</h4>
                      <p>{detail.longTermImpact}</p>
                    </div>
                  )}

                  {decided && (
                    <div className={`tr-decision tr-decision--${BADGE[detail.status]}`}>
                      <strong>{detail.status} by {detail.reviewerName || 'a reviewer'}</strong> · {formatDateTime(detail.reviewedAt)}
                      {detail.reviewNote && <p>&ldquo;{detail.reviewNote}&rdquo;</p>}
                    </div>
                  )}

                  {!decided && (
                    <div className="tr-field">
                      <label htmlFor="tr-note">
                        {rejecting ? 'Reason for rejecting (the member will see this)' : 'Note to the member (optional)'}
                      </label>
                      <textarea
                        id="tr-note"
                        rows={rejecting ? 3 : 2}
                        maxLength={500}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder={rejecting ? 'e.g. Too many leg sessions in a row. Please leave a rest day between them.' : 'Looks balanced. Enjoy!'}
                      />
                    </div>
                  )}

                  {detailError && <div className="tr-error" role="alert">{detailError}</div>}
                </div>

                <div className="tr-modal-actions">
                  <button className="btn-secondary" onClick={close} disabled={deciding}>Close</button>
                  {!decided && (rejecting ? (
                    <>
                      <button className="btn-secondary" onClick={() => { setRejecting(false); setDetailError(''); }} disabled={deciding}>Back</button>
                      <button className="btn-primary tr-danger" onClick={() => decide(false)} disabled={deciding || !note.trim()}>
                        {deciding ? 'Rejecting...' : 'Confirm rejection'}
                      </button>
                    </>
                  ) : (
                    <>
                      <button className="btn-secondary tr-danger-outline" onClick={() => { setRejecting(true); setNote(''); setDetailError(''); }} disabled={deciding}>Reject</button>
                      <button className="btn-primary" onClick={() => decide(true)} disabled={deciding}>
                        {deciding ? 'Verifying...' : 'Verify & approve'}
                      </button>
                    </>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
