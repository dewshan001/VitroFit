import { useState, useEffect, useCallback } from 'react';
import {
  fetchPendingApprovals,
  fetchApprovalDetail,
  approveDietWorkflow,
  rejectDietWorkflow,
} from '../../api/dietPlan';

const RISK_FLAG_TEXT = {
  UNDER_18: 'Under 18',
  MEDICAL_CONDITIONS_PRESENT: 'Medical condition declared',
  BELOW_SAFE_FLOOR: 'Below the 1,200 kcal safe minimum',
  STEEP_DEFICIT: 'Steep calorie deficit',
};

const flagLabel = (flag) => RISK_FLAG_TEXT[flag?.code] || flag?.code || '';
const listOrNone = (list) => (list && list.length ? list.join(', ') : 'None');
const muted = { padding: '40px', textAlign: 'center', color: 'var(--text-muted)' };

function formatDateTime(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

/** Admin Dashboard tab: high-risk diet plans waiting for a nutrition specialist's decision. */
export default function DietApprovalsTab() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [reviewing, setReviewing] = useState(null); // queue row being reviewed
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [declining, setDeclining] = useState(false);
  const [note, setNote] = useState('');
  const [deciding, setDeciding] = useState(false);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setRows((await fetchPendingApprovals()) || []);
    } catch (err) {
      setError('Failed to load diet plans awaiting approval: ' + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadQueue(); }, [loadQueue]);

  const openReview = async (row) => {
    setReviewing(row);
    setDetail(null);
    setDetailError('');
    setDeclining(false);
    setNote('');
    setDetailLoading(true);
    try {
      setDetail(await fetchApprovalDetail(row.id));
    } catch (err) {
      setDetailError(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const closeReview = () => {
    if (deciding) return;
    setReviewing(null);
    setDetail(null);
  };

  const decide = async (decision) => {
    setDeciding(true);
    setDetailError('');
    try {
      if (decision === 'approve') await approveDietWorkflow(reviewing.id, note.trim());
      else await rejectDietWorkflow(reviewing.id, note.trim());
      setReviewing(null);
      setDetail(null);
      loadQueue();
    } catch (err) {
      setDetailError(err.message);
    } finally {
      setDeciding(false);
    }
  };

  const inputs = detail?.inputs;
  const macros = detail?.targets?.macros;

  return (
    <>
      <div className="admin-card">
        {loading ? (
          <div style={muted}>Loading...</div>
        ) : error ? (
          <div style={{ ...muted, color: '#ef4444' }}>{error}</div>
        ) : rows.length === 0 ? (
          <div style={muted}>No diet plans are waiting for approval.</div>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Customer (user ID)</th>
                  <th>Risk</th>
                  <th>Reasons</th>
                  <th>Daily kcal</th>
                  <th>Generated</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>#{r.userId}</td>
                    <td><span className="admin-badge unverified">{r.riskLevel}</span></td>
                    <td>{(r.riskFlags || []).map(flagLabel).join(', ') || '-'}</td>
                    <td>{r.totalCalories ?? '-'}</td>
                    <td>{formatDateTime(r.createdAt)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button className="btn-primary" onClick={() => openReview(r)}>Review</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {reviewing && (
        <div className="admin-modal-overlay">
          <div className="admin-modal" style={{ maxWidth: '720px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="admin-modal-header">
              <h3 className="admin-modal-title">Diet plan review · user #{reviewing.userId}</h3>
              <p className="admin-modal-desc">
                Generated {formatDateTime(reviewing.createdAt)}. Approving makes the plan visible to the customer; declining removes it from their list.
              </p>
            </div>

            {detailLoading && <div style={muted}>Loading...</div>}
            {detailError && <div style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '12px' }}>{detailError}</div>}

            {detail && (
              <>
                <h4 style={{ margin: '0 0 8px' }}>Why it needs review</h4>
                <p style={{ margin: '0 0 16px' }}>
                  Risk: <strong>{detail.riskLevel}</strong>
                  {detail.riskFlags?.length > 0 && <> — {detail.riskFlags.map(flagLabel).join(', ')}</>}
                </p>

                <h4 style={{ margin: '0 0 8px' }}>Customer data</h4>
                {inputs && (
                  <table className="admin-table" style={{ marginBottom: '16px' }}>
                    <tbody>
                      <tr><td>Age / gender</td><td>{inputs.age} · {inputs.gender}</td></tr>
                      <tr><td>Height / weight</td><td>{inputs.heightCm} cm · {inputs.weightKg} kg</td></tr>
                      <tr><td>Activity level</td><td>{inputs.activityLevel}</td></tr>
                      <tr><td>Goal</td><td>{inputs.goal}</td></tr>
                      <tr><td>Medical conditions</td><td>{listOrNone(inputs.medicalConditions)}</td></tr>
                      <tr><td>Dietary restrictions</td><td>{listOrNone(inputs.restrictions)}</td></tr>
                      <tr><td>Dislikes</td><td>{inputs.dislikes || 'None'}</td></tr>
                      <tr><td>Budget</td><td>{inputs.budgetTier}{inputs.budgetCustomAmount ? ` (${inputs.budgetCustomAmount})` : ''}</td></tr>
                      <tr><td>Meals / cooking time</td><td>{inputs.mealFrequency} · {inputs.cookingTime}</td></tr>
                    </tbody>
                  </table>
                )}

                <h4 style={{ margin: '0 0 8px' }}>Generated plan</h4>
                {detail.targets && (
                  <p style={{ margin: '0 0 8px' }}>
                    <strong>{detail.targets.totalCalories} kcal/day</strong>
                    {macros && <> · Protein {macros.protein}g · Carbs {macros.carbs}g · Fat {macros.fat}g</>}
                    {detail.finalOutcome?.withinTolerance === false && ' · outside the usual calorie tolerance'}
                  </p>
                )}
                {(detail.meals || []).map((meal, i) => (
                  <div key={i} style={{ marginBottom: '10px' }}>
                    <strong style={{ textTransform: 'capitalize' }}>{meal.label || meal.type}</strong>
                    <ul style={{ margin: '4px 0 0', paddingLeft: '1.25rem' }}>
                      {(meal.items || []).map((item, j) => (
                        <li key={j}>{item.name}{item.quantity ? ` — ${item.quantity}` : ''}{item.calories != null ? ` (${item.calories} kcal)` : ''}</li>
                      ))}
                    </ul>
                  </div>
                ))}

                {declining && (
                  <div className="admin-form-group" style={{ marginTop: '16px' }}>
                    <label>Reason for declining (required)</label>
                    <input
                      className="admin-input"
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      maxLength={1000}
                      autoFocus
                    />
                  </div>
                )}
              </>
            )}

            <div className="admin-modal-actions">
              <button className="btn-secondary" onClick={closeReview} disabled={deciding}>Close</button>
              {detail && !declining && (
                <>
                  <button
                    className="btn-secondary"
                    style={{ color: '#ef4444', borderColor: '#ef4444' }}
                    onClick={() => setDeclining(true)}
                    disabled={deciding}
                  >
                    Decline
                  </button>
                  <button className="btn-primary" onClick={() => decide('approve')} disabled={deciding}>
                    {deciding ? 'Saving...' : 'Approve'}
                  </button>
                </>
              )}
              {detail && declining && (
                <>
                  <button className="btn-secondary" onClick={() => setDeclining(false)} disabled={deciding}>Back</button>
                  <button
                    className="btn-primary"
                    style={{ background: '#ef4444', borderColor: '#ef4444' }}
                    onClick={() => decide('reject')}
                    disabled={deciding || !note.trim()}
                  >
                    {deciding ? 'Saving...' : 'Confirm Decline'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
