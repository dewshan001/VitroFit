import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  approveWorkflow,
  getAllWorkflows,
  getPendingWorkflows,
  getWorkflow,
  getWorkflowEvents,
  rejectWorkflow,
  reviseWorkflow,
  startWorkflow,
} from '../api/gymAgent';
import './GymApprovalsPage.css';

const ADMIN = 2;
const GYM_OWNER = 3;
const TABS = [
  { id: 'pending', label: 'Awaiting approval', load: getPendingWorkflows },
  { id: 'all', label: 'All runs', load: getAllWorkflows },
];
const REASON_MAX = 500;
const POLL_MS = 2000;
const LIST_POLL_MS = 5000;

function isApprover(role) {
  return role === ADMIN || role === GYM_OWNER || role === 'Admin' || role === 'Gym_Owner';
}

function StatusBadge({ value }) {
  return <span className={`ga-badge ga-${String(value).toLowerCase()}`}>{value}</span>;
}

function Chips({ items, empty }) {
  if (!items?.length) return <span className="ga-muted">{empty}</span>;
  return (
    <ul className="ga-chips">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  );
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '-';
}

export default function GymApprovalsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState(TABS[0]);
  const [items, setItems] = useState([]);
  const [listState, setListState] = useState({ loading: true, error: '' });
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [events, setEvents] = useState([]);
  const [detailState, setDetailState] = useState({ loading: false, error: '' });
  const [reason, setReason] = useState('');
  const [action, setAction] = useState({ busy: false, error: '', message: '' });
  const [showStart, setShowStart] = useState(false);
  const [startForm, setStartForm] = useState({ placeId: '', name: '', website: '', address: '' });
  const [startState, setStartState] = useState({ busy: false, error: '', message: '' });

  // Route guard: signed-in Admin or Gym_Owner only (the API enforces this too).
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem('vitrofitAuth');
      if (!stored) return navigate('/login');
      if (!isApprover(JSON.parse(stored).user?.role)) navigate('/');
    } catch {
      navigate('/login');
    }
  }, [navigate]);

  const loadList = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setListState({ loading: true, error: '' });
    try {
      setItems((await tab.load()) || []);
      setListState({ loading: false, error: '' });
    } catch (err) {
      // A failed background refresh keeps the last good list instead of replacing it with an error.
      if (!quiet) setListState({ loading: false, error: err.message });
    }
  }, [tab]);

  useEffect(() => { loadList(); }, [loadList]);

  // The agents need a minute or two, so a run submitted moments ago is not in the queue yet.
  // Re-check quietly while this page is visible (paused when the browser tab is hidden).
  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) loadList({ quiet: true });
    }, LIST_POLL_MS);
    return () => clearInterval(timer);
  }, [loadList]);

  const loadDetail = useCallback(async (id, { quiet = false } = {}) => {
    if (!quiet) setDetailState({ loading: true, error: '' });
    try {
      const [wf, timeline] = await Promise.all([getWorkflow(id), getWorkflowEvents(id)]);
      setDetail(wf);
      setEvents(timeline || []);
      setDetailState({ loading: false, error: '' });
    } catch (err) {
      setDetailState({ loading: false, error: err.message });
    }
  }, []);

  const select = (id) => {
    setSelectedId(id);
    setDetail(null);
    setEvents([]);
    setReason('');
    setAction({ busy: false, error: '', message: '' });
    loadDetail(id);
  };

  // Deep link from Find Gyms ("Review it"): open that run once on arrival.
  const linkedRun = searchParams.get('run');
  useEffect(() => {
    if (linkedRun) select(linkedRun);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linkedRun]);

  // A run that is still executing (or resuming after a decision) is polled until it settles.
  useEffect(() => {
    if (!selectedId || detail?.status !== 'Running') return undefined;
    const timer = setInterval(() => loadDetail(selectedId, { quiet: true }), POLL_MS);
    return () => clearInterval(timer);
  }, [selectedId, detail?.status, loadDetail]);

  // When a run leaves 'Running' (agents finished, or a decision was applied) refresh the queue,
  // so a run that was submitted a moment ago now appears under "Awaiting approval".
  const previousStatus = useRef(null);
  useEffect(() => {
    const now = detail?.status ?? null;
    if (previousStatus.current === 'Running' && now && now !== 'Running') loadList();
    previousStatus.current = now;
  }, [detail?.status, loadList]);

  const decide = async (kind) => {
    const text = reason.trim();
    if (kind === 'revise' && !text) {
      setAction({ busy: false, error: 'Explain what should change before requesting a revision.', message: '' });
      return;
    }
    setAction({ busy: true, error: '', message: '' });
    try {
      const call = { approve: approveWorkflow, reject: rejectWorkflow, revise: reviseWorkflow }[kind];
      await call(selectedId, text);
      const done = { approve: 'Approved. Publishing as verified...', reject: 'Rejected. Nothing was published.', revise: 'Sent back to the agents for revision.' };
      setAction({ busy: false, error: '', message: done[kind] });
      setReason('');
      await Promise.all([loadDetail(selectedId, { quiet: true }), loadList()]);
    } catch (err) {
      setAction({ busy: false, error: err.message, message: '' });
    }
  };

  const submitStart = async (e) => {
    e.preventDefault();
    setStartState({ busy: true, error: '', message: '' });
    try {
      const body = Object.fromEntries(
        Object.entries(startForm).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v),
      );
      const started = await startWorkflow(body);
      setStartState({ busy: false, error: '', message: 'Review started. It will appear here once the agents finish.' });
      setStartForm({ placeId: '', name: '', website: '', address: '' });
      await loadList();
      select(started.id);
    } catch (err) {
      setStartState({ busy: false, error: err.message, message: '' });
    }
  };

  const facts = detail?.facts;
  const workouts = detail?.recommendations?.workouts ?? [];
  const canDecide = detail?.status === 'AwaitingApproval';

  return (
    <main className="admin-page ga-page">
      <div className="admin-header">
        <div className="admin-header-content">
          <div>
            <h1 className="admin-title">Gym <span>Approvals</span></h1>
            <p className="admin-subtitle">
              Review what the agents found, then approve it as verified, reject it, or send it back.
            </p>
          </div>
          <Link to="/admin" className="ga-link">Back to dashboard</Link>
        </div>
      </div>

      <div className="admin-tabs-bar">
        <div className="admin-tabs-inner" role="tablist" aria-label="Workflow filter">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab.id === t.id}
              className={`admin-tab ${tab.id === t.id ? 'active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="admin-content ga-layout">
        <section className="ga-side" aria-label="Workflows">
          <button className="ga-toggle" onClick={() => loadList()} disabled={listState.loading}>Refresh</button>
          <button className="ga-toggle" onClick={() => setShowStart((v) => !v)} aria-expanded={showStart}>
            {showStart ? 'Hide' : '+ Start a gym review'}
          </button>
          {showStart && (
            <form className="ga-start admin-card" onSubmit={submitStart}>
              {[
                ['placeId', 'Place ID', true],
                ['name', 'Gym name', true],
                ['website', 'Website', false],
                ['address', 'Address', false],
              ].map(([field, label, required]) => (
                <label key={field} className="ga-field">
                  <span>{label}{required && ' *'}</span>
                  <input
                    value={startForm[field]}
                    required={required}
                    maxLength={field === 'placeId' || field === 'name' ? 255 : 500}
                    onChange={(e) => setStartForm((f) => ({ ...f, [field]: e.target.value }))}
                  />
                </label>
              ))}
              {startState.error && <p role="alert" className="ga-error">{startState.error}</p>}
              {startState.message && <p role="status" className="ga-ok">{startState.message}</p>}
              <button className="btn-primary" disabled={startState.busy}>
                {startState.busy ? 'Starting...' : 'Start review'}
              </button>
            </form>
          )}

          <div className="admin-card ga-list">
            {listState.loading ? (
              <p className="ga-state" role="status">Loading...</p>
            ) : listState.error ? (
              <div className="ga-state">
                <p role="alert" className="ga-error">{listState.error}</p>
                <button className="ga-toggle" onClick={loadList}>Retry</button>
              </div>
            ) : items.length === 0 ? (
              <p className="ga-state">
                {tab.id === 'pending'
                  ? 'Nothing is waiting for approval. A submitted gym appears here once the agents finish (about a minute or two); runs that failed are under "All runs".'
                  : 'No runs yet.'}
              </p>
            ) : (
              <ul>
                {items.map((w) => (
                  <li key={w.id}>
                    <button
                      className={`ga-item ${w.id === selectedId ? 'active' : ''}`}
                      onClick={() => select(w.id)}
                      aria-current={w.id === selectedId}
                    >
                      <strong>{w.gymName || w.placeId}</strong>
                      <StatusBadge value={w.status} />
                      <small>{formatDate(w.createdAt)}</small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="ga-detail" aria-live="polite" aria-label="Workflow detail">
          {!selectedId && <div className="admin-card ga-state">Select a run to review it.</div>}
          {selectedId && detailState.loading && <div className="admin-card ga-state" role="status">Loading...</div>}
          {selectedId && detailState.error && (
            <div className="admin-card ga-state"><p role="alert" className="ga-error">{detailState.error}</p></div>
          )}

          {detail && (
            <>
              <div className="admin-card ga-block">
                <div className="ga-head">
                  <h2>{detail.gymName || detail.placeId}</h2>
                  <StatusBadge value={detail.status} />
                </div>
                <dl className="ga-kv">
                  <dt>Approval</dt><dd>{detail.approvalStatus}</dd>
                  <dt>Requested by</dt><dd>{detail.requestedBy}</dd>
                  <dt>Started</dt><dd>{formatDate(detail.createdAt)}</dd>
                  {detail.decidedAt && (
                    <>
                      <dt>Decided</dt>
                      <dd>{formatDate(detail.decidedAt)} by {detail.approvedBy} ({detail.approverRole})</dd>
                    </>
                  )}
                  {detail.approvalNote && (<><dt>Note</dt><dd>{detail.approvalNote}</dd></>)}
                  {detail.finalOutcome && (<><dt>Outcome</dt><dd>{detail.finalOutcome}</dd></>)}
                </dl>
                {detail.status === 'Running' && <p className="ga-muted" role="status">The agents are working...</p>}
              </div>

              {facts && (
                <div className="admin-card ga-block">
                  <h3>What the agents found <small>confidence {Math.round(facts.confidence * 100)}%</small></h3>
                  <h4>Equipment</h4><Chips items={facts.equipment} empty="None found" />
                  <h4>Classes</h4><Chips items={facts.classes} empty="None found" />
                  <dl className="ga-kv">
                    <dt>Phone</dt><dd>{facts.phone || '-'}</dd>
                    <dt>Email</dt><dd>{facts.email || '-'}</dd>
                    <dt>Opening hours</dt><dd>{facts.opening_hours || "-"}</dd>
                  </dl>
                  {facts.evidence?.length > 0 && (
                    <details>
                      <summary>Evidence ({facts.evidence.length})</summary>
                      <ul className="ga-evidence">
                        {facts.evidence.map((e, i) => (
                          <li key={i}><b>{e.field}</b> &ldquo;{e.snippet}&rdquo;</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}

              {workouts.length > 0 && (
                <div className="admin-card ga-block">
                  <h3>Recommended workouts</h3>
                  <div className="ga-workouts">
                    {workouts.map((w) => (
                      <article key={w.name}>
                        <h4>{w.name}</h4>
                        <p className="ga-muted">
                          {w.category} &middot; {w.difficulty} &middot; {w.duration_minutes} min
                        </p>
                        <p>{w.description}</p>
                        <Chips items={w.equipment_used} empty="" />
                      </article>
                    ))}
                  </div>
                </div>
              )}

              {detail.validationResults?.length > 0 && (
                <div className="admin-card ga-block">
                  <h3>Validation</h3>
                  <ul className="ga-validation">
                    {detail.validationResults.map((v) => (
                      <li key={v.attempt}>
                        Attempt {v.attempt}: <b>{v.verdict}</b>
                        {v.violations?.length > 0 && (
                          <ul>{v.violations.map((x, i) => <li key={i}>{x.code}: {x.message}</li>)}</ul>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="admin-card ga-block">
                <h3>Execution history</h3>
                {events.length === 0 ? (
                  <p className="ga-muted">No steps recorded yet.</p>
                ) : (
                  <div className="admin-table-wrap">
                    <table className="admin-table">
                      <thead><tr><th>Agent</th><th>Step / tool</th><th>Result</th><th>Time</th></tr></thead>
                      <tbody>
                        {events.map((e) => (
                          <tr key={e.id}>
                            <td>{e.agent}</td>
                            <td>{e.tool ? `tool: ${e.tool}` : (e.outputSummary || 'step')}</td>
                            <td className={e.ok ? 'ga-ok' : 'ga-error'}>{e.ok ? 'ok' : (e.error || 'failed')}</td>
                            <td>{e.durationMs} ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {canDecide && (
                <div className="admin-card ga-block ga-decision">
                  <h3>Your decision</h3>
                  <p className="ga-muted">Approving publishes this data as <b>verified</b>. Nothing is saved until you approve.</p>
                  <label className="ga-field">
                    <span>Reason / feedback (required to request a revision)</span>
                    <textarea
                      rows={3}
                      maxLength={REASON_MAX}
                      value={reason}
                      onChange={(e) => { setReason(e.target.value); setAction((a) => ({ ...a, error: '' })); }}
                    />
                    <small>{reason.length}/{REASON_MAX}</small>
                  </label>
                  {action.error && <p role="alert" className="ga-error">{action.error}</p>}
                  <div className="ga-buttons">
                    <button className="btn-primary" disabled={action.busy} onClick={() => decide('approve')}>Approve</button>
                    <button className="ga-secondary" disabled={action.busy} onClick={() => decide('revise')}>Request revision</button>
                    <button className="ga-danger" disabled={action.busy} onClick={() => decide('reject')}>Reject</button>
                  </div>
                </div>
              )}
              {action.message && <p role="status" className="ga-ok">{action.message}</p>}
              {action.error && !canDecide && <p role="alert" className="ga-error">{action.error}</p>}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
