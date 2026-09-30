import { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { fitnessRequest } from './api';
import FitnessProfileForm from './FitnessProfileForm';
import WorkoutPlanView from './WorkoutPlanView';
import ProgressForm from './ProgressForm';
import CycleReviewForm from './CycleReviewForm';
import './fitness.css';

export default function AdaptiveFitnessPage() {
  const { isLoggedIn } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [catalog, setCatalog] = useState([]);
  const [selected, setSelected] = useState(null);
  const [schedules, setSchedules] = useState([]);
  const [progressByWeek, setProgressByWeek] = useState({});
  const [editing, setEditing] = useState(false);
  const [history, setHistory] = useState(null);
  const [nextCycle, setNextCycle] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [feedbackTarget, setFeedbackTarget] = useState('page');

  const open = useCallback(async id => {
    const [workflow, audit] = await Promise.all([
      fitnessRequest(`workflows/${id}`),
      fitnessRequest(`workflows/${id}/history`),
    ]);
    let cycle = null;
    try { cycle = await fitnessRequest(`workflows/${id}/next-cycle`); } catch {}
    setSelected(workflow);
    setHistory(audit);
    setNextCycle(cycle);
    if (workflow.plan?.week) setProgressByWeek(current => ({ ...current, [workflow.plan.week]: audit.progress || [] }));
  }, []);

  const refresh = useCallback(async (currentProfile, targetId = null) => {
    const firstPage = await fitnessRequest('workflows?page=1');
    const pages = await Promise.all(Array.from({ length: Math.max(0, Math.ceil(firstPage.total / firstPage.pageSize) - 1) }, (_, index) =>
      fitnessRequest(`workflows?page=${index + 2}`)));
    const summaries = [...firstPage.items, ...pages.flatMap(page => page.items)];
    const details = await Promise.all(summaries.map(item => fitnessRequest(`workflows/${item.id}`)));
    const readySchedules = details.filter(item => item.status === 'Ready' && item.plan)
      .sort((a, b) => a.plan.week - b.plan.week);
    const audits = await Promise.all(readySchedules.map(item =>
      fitnessRequest(`workflows/${item.id}/history`)));
    setProgressByWeek(Object.fromEntries(readySchedules.map((item, index) => [item.plan.week, audits[index].progress || []])));
    setSchedules(currentProfile?.reviewRequired ? [] : readySchedules);
    const latest = details[0];
    const toOpen = targetId ? (details.find(d => d.id === targetId) || latest) : latest;
    if (toOpen && !currentProfile?.reviewRequired) await open(toOpen.id);
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
    })().catch(e => { if (active) { setFeedbackTarget('page'); setError(e.message); } })
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

  async function action(task, target = 'schedule') {
    setBusy(true); setError(''); setNotice(''); setFeedbackTarget(target);
    try { await task(); return true; }
    catch (e) { setFeedbackTarget(target); setError(e.message); return false; }
    finally { setBusy(false); }
  }

  async function generate(previousWorkflowId = null, currentProfile = profile) {
    const workflow = await fitnessRequest('workflows', 'POST', { previousWorkflowId });
    await open(workflow.id);
    await refresh(currentProfile);
    setNotice(workflow.status === 'Ready'
      ? (workflow.plan?.week > 4
          ? `Workout block ${workflow.plan.week - 4} is ready.`
          : `Beginner schedule ${workflow.plan?.week ?? ''} is ready.`)
      : workflow.summary || 'The schedule could not be generated. See failure details below.');
  }

  function profileAfterReview(review) {
    const updated = { ...profile, goal: review.goal, sessionMinutes: review.availableWorkoutMinutes,
      days: review.availableDays, equipment: review.equipment, updatedAt: new Date().toISOString() };
    setProfile(updated);
    return updated;
  }

  if (!isLoggedIn) return <Navigate to="/login" replace />;
  const hasFocusMismatch = selected?.summary?.includes('Exercise does not match this day') ||
    history?.events.some(event => event.step === 'validator' && event.summary.includes('Exercise does not match this day'));
  const recordedProgress = Object.entries(progressByWeek)
    .flatMap(([week, records]) => records.map(record => ({ ...record, week: Number(week) })))
    .sort((a, b) => a.week - b.week || a.day - b.day);
  const fourWeekCycleReady = selected?.status === 'Ready' && selected.plan?.week === 4 &&
    selected.plan.days.every(day => history?.progress.some(progress =>
      progress.day === day.day && (progress.completed || progress.pain)));
  const currentBlockRecorded = selected?.status === 'Ready' && selected.plan?.week > 4 &&
    selected.plan.days.every(day => history?.progress.some(progress =>
      progress.day === day.day && (progress.completed || progress.pain)));
  const cycleExpired = nextCycle?.endDate && nextCycle.endDate < new Date().toISOString().slice(0, 10);
  const cycleBlocksCount = selected?.plan?.week > 4 ? selected.plan.week - 4 : 0;
  const cycleCompleted = Boolean(selected?.plan?.week > 4 && ((cycleBlocksCount > 0 && cycleBlocksCount % 12 === 0 && currentBlockRecorded) || cycleExpired));
  const needsCycleReview = Boolean((fourWeekCycleReady && (!nextCycle || cycleExpired)) || cycleCompleted);

  return <main className="adaptive-fitness">
    <header className="fitness-hero fitness-reveal">
      <div className="fitness-hero-copy">
        <span className="fitness-eyebrow fitness-hero-item fitness-hero-item-1">{schedules.some(s => s.plan?.week > 4) ? 'Adaptive training · Three-month cycle' : 'Adaptive training · Beginner series'}</span>
        <h1 className="fitness-hero-item fitness-hero-item-2"><span className="fitness-hero-outline">Train smarter.</span><br /><span className="fitness-hero-solid">Week by week.</span></h1>
        <p className="fitness-hero-item fitness-hero-item-3">Build a routine around your goals. Your plan adapts as you log progress, with instructor guidance for what comes next.</p>
      </div>
      <div className="fitness-hero-stamp" aria-hidden="true">VF</div>
      <span className="fitness-hero-index">{schedules.some(s => s.plan?.week > 4) ? '05+ — ∞' : '01 — 04'} <i /> {schedules.some(s => s.plan?.week > 4) ? 'ADAPTIVE CYCLE' : 'SELF-GUIDED PLAN'}</span>
    </header>
    {feedbackTarget === 'page' && error && <p role="alert" className="fitness-error fitness-page-feedback">{error}</p>}
    {loaded && (!profile || editing) && <FitnessProfileForm key={profile?.updatedAt || 'new'} initial={profile} busy={busy}
      error={feedbackTarget === 'profile' ? error : ''} notice={feedbackTarget === 'profile' ? notice : ''}
      working={feedbackTarget === 'profile' && busy}
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
      }, 'profile')} />}

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
          setProfile(null); setSelected(null); setHistory(null); setNextCycle(null); setSchedules([]); setEditing(true);
          setNotice('Fitness profile and its schedules were deleted. Your VitroFit account is unchanged.');
        }, 'profile')}>Delete fitness profile</button>
      </div>
      {feedbackTarget === 'profile' && error && <p role="alert" className="fitness-error fitness-inline-feedback">{error}</p>}
      {feedbackTarget === 'profile' && notice && <p role="status" className="fitness-notice fitness-inline-feedback">{notice}</p>}
    </section>}

    {!selected && profile?.reviewRequired && <p role="status" className="fitness-notice">Automated scheduling is paused because your profile indicates a health concern or need for review. If you selected this by mistake and it does not apply to you, update the checkbox before saving.</p>}
    {!selected && profile && !profile.reviewRequired && schedules.length === 0 && <p className="fitness-empty-state">No schedule is available yet. Edit and save your profile to generate week 1.</p>}

    {!profile && loaded && <p className="fitness-empty-state">Create a fitness profile to generate your first schedule.</p>}

    {selected && <section className="fitness-panel fitness-current-panel fitness-reveal">
      <div className="fitness-section-heading">
        <div>
          <span className="fitness-eyebrow">
            {selected.plan?.week > 4 ? 'Three-month schedule · Workout plan' : 'Your training block'}
          </span>
          <h2>
            {selected.plan?.week > 4
              ? `Workout block ${selected.plan?.week - 4}`
              : selected.plan?.week
              ? `Beginner week ${selected.plan?.week} of 4`
              : 'Schedule status'}
          </h2>
        </div>
        {selected.status !== 'Ready' && <span className={`fitness-status fitness-status-${selected.status.toLowerCase()}`}>{selected.status}</span>}
      </div>

      {selected.status === 'Ready' && selected.plan && <div className="fitness-plan-content">
        <WorkoutPlanView
          key={`${selected.id}-${selected.version || 0}`}
          plans={schedules.some(s => s.id === selected.id) ? schedules : [...schedules, selected].filter(Boolean)}
          catalog={catalog}
          progressByWeek={progressByWeek}
        />
        <div className="fitness-plan-guidance">
          <div className="fitness-progression-note"><span className="fitness-eyebrow">Progression guidance</span><p>{selected.summary}</p></div>
          <p className="fitness-safety-note"><strong>Safety reminder</strong>{selected.safetyNote}</p>
        </div>
      </div>}
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
      {fourWeekCycleReady && <section className="fitness-cycle-result" aria-label="Next training block">
        <p role="status" className="fitness-notice fitness-instructor-handoff"><strong>You have completed the four beginner schedules!</strong> Review your current condition, pain or injuries, goals, available time, and equipment before continuing.</p>
        <button disabled={busy} onClick={() => action(() => generate(selected.id))}>Generate 3-Month Schedule</button>
      </section>}
      {selected.plan?.week > 4 && <section className="fitness-cycle-result" aria-label="Continue three-month training cycle">
        {cycleCompleted ? <>
          <p role="status" className="fitness-notice"><strong>Your three-month training cycle is complete.</strong> Review your condition, pain, goals, available workout time, and equipment to start your next 3-month training cycle.</p>
          {needsCycleReview && <CycleReviewForm profile={profile} busy={busy} isFirstCycle={false} onSubmit={review => action(async () => {
            const cycle = await fitnessRequest(`workflows/${selected.id}/next-cycle`, 'POST', review);
            setNextCycle(cycle);
            await generate(selected.id, profileAfterReview(review));
            setNotice('A new three-month training cycle has started with your next workout block.');
          })} />}
        </> : <>
          {currentBlockRecorded
            ? <button disabled={busy} onClick={() => action(() => generate(selected.id))}>Generate Next 3-Month Schedule Block</button>
            : <p className="fitness-guidance-copy">Record each workout day, including performance, effort, and any affected body area. Pain is saved and does not stop the whole program.</p>}
        </>}
      </section>}
      {selected.status === 'Ready' && selected.plan && !fourWeekCycleReady && !currentBlockRecorded && <>
        <ProgressForm key={selected.id} workflow={selected} progress={history?.progress || []}
          previousWeekProgress={progressByWeek[selected.plan.week - 1] || []} busy={busy}
          error={feedbackTarget === 'progress' ? error : ''} notice={feedbackTarget === 'progress' ? notice : ''}
          working={feedbackTarget === 'progress' && busy} onSave={data => action(async () => {
          await fitnessRequest(`workflows/${selected.id}/progress`, 'PUT', data);
          await open(selected.id);
          setNotice('Progress saved.');
          return true;
        }, 'progress')} />
        {selected.plan.week < 4 && <>
          <button disabled={busy || !selected.plan.days.every(day => history?.progress.some(progress => progress.day === day.day && (progress.completed || progress.pain)))}
            onClick={() => action(() => generate(selected.id))}>Create week {selected.plan.week + 1} of 4 from my progress</button>
          {!selected.plan.days.every(day => history?.progress.some(progress => progress.day === day.day && (progress.completed || progress.pain))) &&
            <p className="fitness-guidance-copy">Record each scheduled weekday before creating the next week. Pain reports remain in your history and guide a more conservative schedule.</p>}
        </>}
        {selected.plan.week === 4 && !fourWeekCycleReady &&
          <p className="fitness-guidance-copy">Record every scheduled day in week four to finish the four-week block and unlock your three-month schedule.</p>}
      </>}
      {feedbackTarget === 'schedule' && error && <p role="alert" className="fitness-error fitness-inline-feedback">{error}</p>}
      {feedbackTarget === 'schedule' && notice && <p role="status" className="fitness-notice fitness-inline-feedback">{notice}</p>}
      {feedbackTarget === 'schedule' && busy && <p role="status" className="fitness-notice fitness-inline-feedback">Working… generation can take up to two minutes. Do not submit again.</p>}
      {['Failed', 'Running'].includes(selected.status) && <button disabled={busy} onClick={() => action(async () => {
        await fitnessRequest(`workflows/${selected.id}/retry`, 'POST', {});
        await open(selected.id);
      })}>Retry failed / interrupted request</button>}
      {selected.status === 'Ready' && selected.plan && !schedules.some(s => s.previousWorkflowId === selected.id) && <button className="fitness-btn-secondary" disabled={busy} onClick={() => action(async () => {
        const updated = await fitnessRequest(`workflows/${selected.id}/regenerate`, 'POST', {});
        await refresh(profile, selected.id);
        setNotice(updated.status === 'Ready'
          ? (updated.plan?.week > 4 ? `Workout block ${updated.plan.week - 4} regenerated.` : `Week ${updated.plan?.week} regenerated.`)
          : updated.summary || 'Failed to regenerate schedule.');
      })}>↻ Regenerate Schedule</button>}
      <details className="fitness-activity-disclosure">
        <summary><span><small>WORKFLOW HISTORY</small><strong>Schedule activity</strong></span><i aria-hidden="true">+</i></summary>
        {history?.events.length ? <ol className="fitness-activity-timeline">{history.events.map((event, index) =>
          <li className="fitness-activity-item" key={event.id}>
            <span className="fitness-activity-marker">{String(index + 1).padStart(2, '0')}</span>
            <div className="fitness-activity-content">
              <div className="fitness-activity-heading"><strong>{event.step}</strong><span>{event.durationMs} ms</span></div>
              <p>{event.summary}</p>
              <details className="fitness-activity-data"><summary>View structured data</summary><pre>{JSON.stringify(event.snapshot, null, 2)}</pre></details>
            </div>
          </li>)}</ol> : <p className="fitness-activity-empty">No workflow activity has been recorded.</p>}
      </details>
      <section className="fitness-recorded-progress" aria-labelledby="fitness-recorded-progress-title">
        <div className="fitness-recorded-progress-heading">
          <span className="fitness-eyebrow">Training log</span>
          <h3 id="fitness-recorded-progress-title">Recorded progress</h3>
        </div>
        {recordedProgress.length ? [...new Set(recordedProgress.map(record => record.week))].map(week => {
            const weekRecords = recordedProgress.filter(record => record.week === week);
            const completedCount = weekRecords.filter(record => record.completed).length;
            const weekPlan = schedules.find(item => item.plan.week === week)?.plan;
            return <details className="fitness-recorded-week" key={week}>
              <summary><span>{week <= 4 ? `Week ${week}` : `Workout block ${week - 4}`}</span><small>{completedCount} of {weekPlan?.days.length ?? weekRecords.length} workouts complete</small><i aria-hidden="true">+</i></summary>
              <ul>{weekRecords.map(p => {
                const dayIndex = weekPlan?.days.findIndex(planDay => planDay.day === p.day) ?? -1;
                return <li key={`${p.week}-${p.day}`}>
                  <span className="fitness-recorded-day"><strong>Day {String(dayIndex >= 0 ? dayIndex + 1 : p.day).padStart(2, '0')}</strong><span>{['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][p.day - 1]}</span></span>
                  <span className={`fitness-recorded-status${p.completed ? ' is-complete' : ' is-incomplete'}`}>{p.completed ? 'Completed' : 'Incomplete'}</span>
                  <span className="fitness-recorded-effort"><strong>{p.rpe}<small>/10</small></strong><span>Effort</span></span>
                  <span className="fitness-recorded-date">{p.performedOn}</span>
                  {p.pain && <span className="fitness-recorded-pain">Pain: {(p.affectedAreas || []).join(', ') || 'area not specified'}</span>}
                </li>;
              })}</ul>
            </details>;
        }) : <p>No sessions have been recorded yet.</p>}
      </section>
    </section>}
  </main>;
}
