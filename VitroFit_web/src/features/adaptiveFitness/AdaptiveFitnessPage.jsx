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

  useEffect(() => {
    const elements = document.querySelectorAll('.adaptive-fitness .fitness-reveal');
    if (!('IntersectionObserver' in window)) {
      elements.forEach(element => element.classList.add('visible'));
      return undefined;
    }

    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    elements.forEach(element => observer.observe(element));
    return () => observer.disconnect();
  }, [loaded, profile, editing, selected, schedules.length]);

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
    setNotice(workflow.status === 'Ready'
      ? `Beginner schedule ${workflow.plan?.week ?? ''} is ready.`
      : workflow.summary || 'The schedule could not be generated. See failure details below.');
  }

  if (!isLoggedIn) return <Navigate to="/login" replace />;
  const hasFocusMismatch = selected?.summary?.includes('Exercise does not match this day') ||
    history?.events.some(event => event.step === 'validator' && event.summary.includes('Exercise does not match this day'));

  return <main className="adaptive-fitness">
    <header className="fitness-hero fitness-reveal">
      <div className="fitness-hero-copy">
        <span className="fitness-eyebrow fitness-hero-item fitness-hero-item-1">Adaptive training · Beginner series</span>
        <h1 className="fitness-hero-item fitness-hero-item-2"><span className="fitness-hero-outline">Train smarter.</span><br /><span className="fitness-hero-solid">Week by week.</span></h1>
        <p className="fitness-hero-item fitness-hero-item-3">Build a routine around your goals. Your plan adapts as you log progress, with instructor guidance for what comes next.</p>
      </div>
      <div className="fitness-hero-stamp" aria-hidden="true">VF</div>
      <span className="fitness-hero-index">01 — 04 <i /> SELF-GUIDED PLAN</span>
    </header>
    {error && <p role="alert" className="fitness-error">{error}</p>}
    {notice && <p role="status" className="fitness-notice">{notice}</p>}
    {busy && <p role="status" className="fitness-notice">Working… generation can take up to two minutes. Do not submit again.</p>}
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

    {profile && !editing && <section className="fitness-panel fitness-profile-panel fitness-reveal">
      <div className="fitness-section-heading"><div><span className="fitness-eyebrow">Your details</span><h2>Your fitness profile</h2></div><span className="fitness-profile-tag">PROFILE SAVED</span></div>
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

    {!selected && profile?.reviewRequired && <p role="status" className="fitness-notice">Automated scheduling is paused because your profile indicates a health concern or need for review. If you selected this by mistake and it does not apply to you, update the checkbox before saving.</p>}
    {!selected && profile && !profile.reviewRequired && schedules.length === 0 && <p className="fitness-empty-state">No schedule is available yet. Edit and save your profile to generate week 1.</p>}

    {!profile && loaded && <p className="fitness-empty-state">Create a fitness profile to generate your first schedule.</p>}

    {selected && <section className="fitness-panel fitness-current-panel fitness-reveal">
      {selected.status === 'Ready' ? <details className="fitness-plan-disclosure">
        <summary>
          <span className="fitness-plan-title"><span className="fitness-plan-kicker">Your training block</span><strong>Current week {selected.plan?.week} of 4</strong></span>
          <span className={`fitness-status fitness-status-${selected.status.toLowerCase()}`}>{selected.status}</span>
          <span className="fitness-plan-toggle"><span className="fitness-view-label">View plan</span><i aria-hidden="true">+</i></span>
        </summary>
        <div className="fitness-plan-content">
          <p className="fitness-summary-line">{selected.summary}</p><p className="fitness-safety-note">{selected.safetyNote}</p>
          <WorkoutPlanView plans={schedules} catalog={catalog} />
        </div>
      </details> : <div className="fitness-section-heading"><div><span className="fitness-eyebrow">Plan update</span><h2>Schedule status</h2></div><span className={`fitness-status fitness-status-${selected.status.toLowerCase()}`}>{selected.status}</span></div>}
      {selected.status !== 'Ready' && <><p className="fitness-summary-line">{selected.summary}</p><p className="fitness-safety-note">{selected.safetyNote}</p></>}
      {selected.status === 'ReviewRequired' && <p role="status" className="fitness-notice">The agent paused because your profile or progress indicates a concern. Please speak with an instructor or qualified health professional before continuing.</p>}
      {selected.status === 'Failed' && <section className="fitness-error" aria-live="polite">
        <h3>Failure details</h3>
        <p>{selected.summary}</p>
        {history?.events.filter(event => ['planner', 'validator'].includes(event.step)).map((event, index) =>
          <p key={`${event.id}-${index}`}><strong>{event.step}:</strong> {event.summary}</p>)}
        {hasFocusMismatch && <p>This workflow includes a schedule-rule mismatch. The updated agent replaces incompatible exercise selections with approved catalog items before validation.</p>}
        {selected.summary.startsWith('Agent unavailable or interrupted') && <p>The agent service did not complete this request. Check that both the ASP.NET API and Python agent are running, then retry. The previous request’s activity entries may help identify which step stopped.</p>}
      </section>}
      {selected.status === 'Failed' && !selected.previousWorkflowId && <button disabled={busy}
        onClick={() => action(() => generate(null))}>Start a fresh week 1 with my saved profile</button>}
      {selected.status === 'Ready' && selected.plan && <>
        <ProgressForm key={selected.id} workflow={selected} busy={busy} onSave={data => action(async () => {
          await fitnessRequest(`workflows/${selected.id}/progress`, 'PUT', data);
          await open(selected.id);
          setNotice('Progress saved.');
        })} />
        {selected.plan.week < 4 && <button disabled={busy || history?.progress.length !== selected.plan.days.length}
          onClick={() => action(() => generate(selected.id))}>Create week {selected.plan.week + 1} of 4 from my progress</button>}
        {selected.plan.week === 4 && <p role="status" className="fitness-notice"><strong>You have completed the four beginner schedules.</strong> Meet an instructor to plan the next stage of your training.</p>}
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
