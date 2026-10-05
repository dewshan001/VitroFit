import { useState, useEffect, useCallback } from 'react';
import {
  getGymApplications,
  getGymApplication,
  approveGymApplication,
  rejectGymApplication,
} from '../../api/admin';
import './GymApplicationsTab.css';

const FILTERS = [
  { id: 'Pending', label: 'Pending' },
  { id: 'Approved', label: 'Approved' },
  { id: 'Rejected', label: 'Rejected' },
];

const BADGE = { Pending: 'unverified', Approved: 'verified', Rejected: 'rejected' };
const muted = { padding: '40px', textAlign: 'center', color: 'var(--text-muted)' };

function formatDateTime(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

/** The URL is shown to admins as a link, so only allow web addresses (never javascript: and similar). */
function safeHref(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : null;
  } catch {
    return null;
  }
}

/** Admin Dashboard tab: gym owner applications waiting for (or already given) a decision. */
export default function GymApplicationsTab() {
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
  const [lightbox, setLightbox] = useState(null);
  const [banner, setBanner] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getGymApplications(status);
      setRows(data?.items || []);
      setCounts(data?.counts || { pending: 0, approved: 0, rejected: 0 });
    } catch (err) {
      setError('Failed to load gym applications: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => { load(); }, [load]);

  const open = async (row) => {
    setOpenId(row.id);
    setDetail(null);
    setDetailError('');
    setRejecting(false);
    setNote('');
    setBanner('');
    setDetailLoading(true);
    try {
      setDetail(await getGymApplication(row.id));
    } catch (err) {
      setDetailError(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const close = () => {
    if (deciding) return;
    setOpenId(null);
    setDetail(null);
    setLightbox(null);
  };

  const decide = async (decision) => {
    setDeciding(true);
    setDetailError('');
    try {
      const result = decision === 'approve'
        ? await approveGymApplication(openId, note.trim())
        : await rejectGymApplication(openId, note.trim());
      setBanner(result?.warning
        ? result.warning
        : `Application ${decision === 'approve' ? 'approved' : 'rejected'} and the owner was emailed.`);
      setOpenId(null);
      setDetail(null);
      load();
    } catch (err) {
      setDetailError(err.message);
    } finally {
      setDeciding(false);
    }
  };

  useEffect(() => {
    if (!openId) return undefined;
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      if (lightbox) setLightbox(null);
      else close();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openId, lightbox, deciding]);

  const gallery = (title, urls) => (
    <div className="ga-section">
      <h4>{title} <span>({urls.length})</span></h4>
      <ul className="ga-photos">
        {urls.map((url) => (
          <li key={url}>
            <button type="button" onClick={() => setLightbox(url)} aria-label={`Open ${title.toLowerCase()} full size`}>
              <img src={url} alt={title} loading="lazy" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );

  const website = detail ? safeHref(detail.website) : null;
  const licence = detail?.licenseUrl ? safeHref(detail.licenseUrl) : null;

  return (
    <>
      {banner && (
        <div className="ga-banner" role="status">
          {banner}
          <button type="button" onClick={() => setBanner('')} aria-label="Dismiss">×</button>
        </div>
      )}

      <div className="ga-filters" role="tablist" aria-label="Application status">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            role="tab"
            aria-selected={status === f.id}
            className={`ga-filter ${status === f.id ? 'active' : ''}`}
            onClick={() => setStatus(f.id)}
          >
            {f.label}
            <span className={`ga-count ${f.id === 'Pending' && counts.pending > 0 ? 'hot' : ''}`}>{counts[f.id.toLowerCase()] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="admin-card">
        {loading ? (
          <div style={muted}>Loading...</div>
        ) : error ? (
          <div style={{ ...muted, color: '#ef4444' }}>{error}</div>
        ) : rows.length === 0 ? (
          <div style={muted}>No {status.toLowerCase()} gym applications.</div>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Gym</th>
                  <th>City</th>
                  <th>Owner</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td><strong>{r.gymName}</strong></td>
                    <td>{r.city}</td>
                    <td>
                      {r.ownerName}
                      <div className="email">{r.ownerEmail}</div>
                    </td>
                    <td><span className={`admin-badge ${BADGE[r.status] || ''}`}>{r.status}</span></td>
                    <td className="date">{formatDateTime(r.createdAt)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button className="btn-primary" onClick={() => open(r)}>Review</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {openId && (
        <div className="admin-modal-overlay" onClick={close}>
          <div
            className="admin-modal ga-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Gym application review"
            onClick={(e) => e.stopPropagation()}
          >
            {detailLoading && <div style={muted}>Loading application...</div>}
            {!detailLoading && !detail && detailError && <div style={{ ...muted, color: '#ef4444' }}>{detailError}</div>}

            {detail && (
              <>
                <div className="admin-modal-header ga-head">
                  <div>
                    <h3 className="admin-modal-title">{detail.gymName}</h3>
                    <p className="admin-modal-desc">
                      {detail.address}, {detail.city} · submitted {formatDateTime(detail.createdAt)}
                    </p>
                  </div>
                  <span className={`admin-badge ${BADGE[detail.status] || ''}`}>{detail.status}</span>
                </div>

                <div className="ga-body">
                  <dl className="ga-facts">
                    <dt>Applicant</dt>
                    <dd>
                      {detail.ownerName} <span className="ga-pill">{detail.ownerRole}</span>
                      <div className="email">{detail.ownerEmail}{detail.ownerPhone ? ` · ${detail.ownerPhone}` : ''}</div>
                      {!detail.ownerEmailVerified && <div className="ga-warn">Email not verified yet</div>}
                    </dd>
                    <dt>Website</dt>
                    <dd>
                      {website
                        ? <a href={website} target="_blank" rel="noopener noreferrer">{detail.website}</a>
                        : <span className="ga-warn">{detail.website} (not a valid web address)</span>}
                    </dd>
                    <dt>Gym contact</dt>
                    <dd>{detail.gymPhone} · {detail.contactEmail}</dd>
                    {detail.openingHours && (<><dt>Hours</dt><dd>{detail.openingHours}</dd></>)}
                    <dt>Licence</dt>
                    <dd>
                      {licence
                        ? <a href={licence} target="_blank" rel="noopener noreferrer">Open document</a>
                        : <span className="ga-muted">None provided</span>}
                    </dd>
                  </dl>

                  <div className="ga-section">
                    <h4>About</h4>
                    <p className="ga-about">{detail.description}</p>
                  </div>

                  <div className="ga-section">
                    <h4>Equipment <span>({detail.equipment.length})</span></h4>
                    <div className="ga-chips">{detail.equipment.map((t) => <span key={t}>{t}</span>)}</div>
                    {detail.classes.length > 0 && (
                      <>
                        <h4 style={{ marginTop: '14px' }}>Classes <span>({detail.classes.length})</span></h4>
                        <div className="ga-chips ga-chips--alt">{detail.classes.map((t) => <span key={t}>{t}</span>)}</div>
                      </>
                    )}
                  </div>

                  {gallery('Gym photos', detail.gymPhotoUrls)}
                  {gallery('Equipment photos', detail.equipmentPhotoUrls)}

                  {detail.reviewNote && (
                    <div className="ga-section">
                      <h4>Last decision note</h4>
                      <p className="ga-about">{detail.reviewNote}</p>
                      <p className="ga-muted">{formatDateTime(detail.reviewedAt)}</p>
                    </div>
                  )}

                  {rejecting && (
                    <div className="admin-form-group">
                      <label htmlFor="ga-note">Reason for rejecting (the owner will see this)</label>
                      <textarea
                        id="ga-note"
                        className="admin-input"
                        rows={3}
                        maxLength={500}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="e.g. The website could not be verified. Please add photos of the equipment you listed."
                      />
                    </div>
                  )}
                  {!rejecting && detail.status !== 'Approved' && (
                    <div className="admin-form-group">
                      <label htmlFor="ga-approve-note">Note to the owner (optional)</label>
                      <input
                        id="ga-approve-note"
                        className="admin-input"
                        maxLength={500}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="Welcome aboard!"
                      />
                    </div>
                  )}

                  {detailError && <div className="ga-error" role="alert">{detailError}</div>}
                </div>

                <div className="admin-modal-actions">
                  <button className="btn-secondary" onClick={close} disabled={deciding}>Close</button>

                  {rejecting ? (
                    <>
                      <button className="btn-secondary" onClick={() => { setRejecting(false); setDetailError(''); }} disabled={deciding}>Back</button>
                      <button className="btn-primary ga-danger" onClick={() => decide('reject')} disabled={deciding || !note.trim()}>
                        {deciding ? 'Rejecting...' : 'Confirm rejection'}
                      </button>
                    </>
                  ) : (
                    <>
                      {detail.status !== 'Rejected' && (
                        <button className="btn-secondary ga-danger-outline" onClick={() => { setRejecting(true); setNote(''); setDetailError(''); }} disabled={deciding}>
                          {detail.status === 'Approved' ? 'Revoke approval' : 'Reject'}
                        </button>
                      )}
                      {detail.status !== 'Approved' && (
                        <button className="btn-primary" onClick={() => decide('approve')} disabled={deciding}>
                          {deciding ? 'Approving...' : 'Approve'}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {lightbox && (
        <div className="ga-lightbox" role="dialog" aria-label="Photo preview" onClick={() => setLightbox(null)}>
          <img src={lightbox} alt="Full size" />
          <button type="button" aria-label="Close preview" onClick={() => setLightbox(null)}>×</button>
        </div>
      )}
    </>
  );
}
