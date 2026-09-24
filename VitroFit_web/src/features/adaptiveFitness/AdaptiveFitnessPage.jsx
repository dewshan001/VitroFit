import { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { fitnessRequest } from './api';
import FitnessProfileForm from './FitnessProfileForm';
import WorkoutPlanView from './WorkoutPlanView';
import ProgressForm from './ProgressForm';
import './fitness.css';

export default function AdaptiveFitnessPage() {
  const { isLoggedIn } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [catalog, setCatalog] = useState([]);
  const [selected, setSelected] = useState(null);
  const [schedules, setSchedules] = useState([]);
  const [editing, setEditing] = useState(false);
  const [history, setHistory] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const open = useCallback(async id => {
    const [workflow, audit] = await Promise.all([
      fitnessRequest(`workflows/${id}`),
      fitnessRequest(`workflows/${id}/history`),
    ]);
    setSelected(workflow);
    setHistory(audit);
  }, []);

  const refresh = useCallback(async currentProfile => {
    const data = await fitnessRequest('workflows?page=1');
    const details = await Promise.all(data.items.map(item => fitnessRequest(`workflows/${item.id}`)));
    const readySchedules = details.filter(item => item.status === 'Ready' && item.plan)
      .sort((a, b) => a.plan.week - b.plan.week);
    setSchedules(currentProfile?.reviewRequired ? [] : readySchedules);
    const latest = details[0];
    if (latest && !currentProfile?.reviewRequired) await open(latest.id);
    else if (latest) {
      setSelected(latest.status === 'ReviewRequired' ? latest : null);
      setHistory(null);
    } else { setSelected(null); setHistory(null); }
  }, [open]);

  useEffect(() => {
    if (!isLoggedIn) return;
    let active = true;
    (async () => {
      const exercisesRequest = fitnessRequest('exercises');
      let savedProfile = null;
      try { savedProfile = await fitnessRequest('profile'); }
      catch (e) { if (e.message !== 'Create your fitness profile first.') throw e; }
      const exercises = await exercisesRequest;
        if (!active) return;
        setCatalog(exercises); setProfile(savedProfile); setEditing(!savedProfile);
        await refresh(savedProfile);
    })().catch(e => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, [isLoggedIn, refresh]);

  async function action(task) {
    setBusy(true); setError(''); setNotice('');
    try { await task(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function generate(previousWorkflowId = null, currentProfile = profile) {
    const workflow = await fitnessRequest('workflows', 'POST', { previousWorkflowId });
    await open(workflow.id);
    await refresh(currentProfile);
    setNotice(`Beginner schedule ${workflow.plan?.week ?? ''} is ready.`);
  }

  if (!isLoggedIn) return <Navigate to="/login" replace />;

  return <main className="adaptive-fitness">
    <h1>Adaptive beginner schedules</h1>
    <p>Choose your target and save your profile. The agent creates the first week, then adapts the next three weeks using your progress. Meet an instructor after week four to continue.</p>
    {error && <p role="alert" className="fitness-error">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {busy && <p role="status">Working… generation can take up to two minutes. Do not submit again.</p>}
    {loaded && (!profile || editing) && <FitnessProfileForm key={profile?.updatedAt || 'new'} initial={profile} busy={busy}
      createSchedule={!selected || (selected.status === 'ReviewRequired' && !selected.previousWorkflowId)}
      onCancel={profile ? () => setEditing(false) : undefined} onSave={data => action(async () => {
      const saved = await fitnessRequest('profile', 'PUT', data);
      setProfile(saved);
      setEditing(false);
      if (saved.reviewRequired) {
        setSelected(null); setHistory(null); setSchedules([]);
        setNotice('Profile saved. Your answer indicates a possible safety concern, so the self-scheduling agent is paused. Please get appropriate professional guidance.');
        return;
      }
      if (!selected || (selected.status === 'ReviewRequired' && !selected.previousWorkflowId)) await generate(null, saved);
      else setNotice('Profile saved. Continue your current beginner schedule below.');
    })} />}

    {profile && !editing && <section>
      <h2>Your fitness profile</h2>
      <div className="fitness-profile-summary">
        <span><strong>Target:</strong> {profile.goal.replaceAll('_', ' ')}</span>
        <span><strong>Age:</strong> {profile.age}</span>
        <span><strong>Height:</strong> {profile.heightCm} cm</span>
        <span><strong>Weight:</strong> {profile.weightKg} kg</span>
        <span><strong>Days:</strong> {profile.days.map(day => ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day - 1]).join(', ')}</span>
        <span><strong>Session:</strong> {profile.sessionMinutes} min</span>
      </div>
      <div className="fitness-profile-actions">
        <button disabled={busy} onClick={() => setEditing(true)}>Edit profile</button>
        <button className="fitness-danger" disabled={busy} onClick={() => action(async () => {
          if (!window.confirm('Delete your fitness profile, schedules, and progress? Your VitroFit account will remain.')) return;
          await fitnessRequest('profile', 'DELETE');
          setProfile(null); setSelected(null); setHistory(null); setSchedules([]); setEditing(true);
          setNotice('Fitness profile and its schedules were deleted. Your VitroFit account is unchanged.');
        })}>Delete fitness profile</button>
      </div>
    </section>}

    {!selected && profile?.reviewRequired && <p role="status">Automated scheduling is paused because your profile indicates a health concern or need for review. If you selected this by mistake and it does not apply to you, update the checkbox before saving.</p>}
    {!selected && profile && !profile.reviewRequired && schedules.length === 0 && <p>No schedule is available yet. Edit and save your profile to generate week 1.</p>}

    {!profile && loaded && <p>Create a fitness profile to generate your first schedule.</p>}

    {selected && <section>
      <h2>{selected.status === 'Ready' ? `Current week ${selected.plan?.week} of 4` : 'Schedule status'}</h2>
      <p>{selected.summary}</p><p>{selected.safetyNote}</p>
      {selected.status === 'Ready' && <WorkoutPlanView plans={schedules} catalog={catalog} />}
      {selected.status === 'ReviewRequired' && <p role="status">The agent paused because your profile or progress indicates a concern. Please speak with an instructor or qualified health professional before continuing.</p>}
      {selected.status === 'Failed' && <section className="fitness-error" aria-live="polite">
        <h3>Failure details</h3>
        <p>{selected.summary}</p>
        {history?.events.filter(event => ['planner', 'validator'].includes(event.step)).map((event, index) =>
          <p key={`${event.id}-${index}`}><strong>{event.step}:</strong> {event.summary}</p>)}
        <p><code>MODEL_OUTPUT_TRUNCATED_TOKEN_LIMIT</code> confirms output truncation at the model token cap. HTTP 429 indicates rate limiting; HTTP 401/403 indicates provider key or permission trouble; HTTP 402 usually means provider credits/payment are unavailable. Timeout/connection codes indicate a network or provider delay. Validation messages point to a plan-rule mismatch.</p>
      </section>}
      {selected.status === 'Ready' && selected.plan && <>
        <ProgressForm key={selected.id} workflow={selected} busy={busy} onSave={data => action(async () => {
          await fitnessRequest(`workflows/${selected.id}/progress`, 'PUT', data);
          await open(selected.id);
          setNotice('Progress saved.');
        })} />
        {selected.plan.week < 4 && <button disabled={busy || history?.progress.length !== selected.plan.days.length}
          onClick={() => action(() => generate(selected.id))}>Create week {selected.plan.week + 1} of 4 from my progress</button>}
        {selected.plan.week === 4 && <p role="status"><strong>You have completed the four beginner schedules.</strong> Meet an instructor to plan the next stage of your training.</p>}
      </>}
      {['Failed', 'Running'].includes(selected.status) && <button disabled={busy} onClick={() => action(async () => {
        await fitnessRequest(`workflows/${selected.id}/retry`, 'POST', {});
        await open(selected.id);
      })}>Retry failed / interrupted request</button>}
      <details><summary>Schedule activity</summary>
        <ol>{history?.events.map(event => <li key={event.id}>
          <strong>{event.step}</strong>: {event.summary} ({event.durationMs} ms)
          <details><summary>Structured step data</summary><pre>{JSON.stringify(event.snapshot, null, 2)}</pre></details>
        </li>)}</ol>
        <h3>Recorded progress</h3>
        <ul>{history?.progress.map(p => <li key={p.id}>Day {p.day}: {p.completed ? 'Completed' : 'Incomplete'}, effort {p.rpe}/10{p.pain ? ', pain reported' : ''}</li>)}</ul>
      </details>
    </section>}
  </main>;
}
