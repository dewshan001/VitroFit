import { useEffect, useState } from 'react';

export default function ProgressForm({ workflow, progress = [], previousWeekProgress = [], onSave, busy, error, notice, working }) {
  const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  // Weeks 1–4: always single-day. Week 5+: always batch (all days at once).
  const blockPlan = workflow.plan.week > 4;
  const batchMode = blockPlan;
  const bodyAreas = ['chest', 'triceps', 'arms', 'back', 'legs', 'shoulders', 'core', 'full body'];
  const sessionWeekdays = workflow.plan.days.map(d => d.day);
  const completedRecords = progress.filter(record => record.completed || record.pain);
  const painReported = progress.some(record => record.pain);
  const completedDays = new Set(completedRecords.map(record => record.day));
  const availableDays = workflow.plan.days.filter(planDay => !completedDays.has(planDay.day));
  const initialDay = availableDays[0]?.day ?? workflow.plan.days[0].day;
  const [day, setDay] = useState(initialDay);
  const [rpe, setRpe] = useState(5);
  const [incomplete, setIncomplete] = useState(false);
  const [pain, setPain] = useState(false);
  const [affectedAreas, setAffectedAreas] = useState([]);
  const [noPainConfirmed, setNoPainConfirmed] = useState(false);

  const latestCompletedDate = progress.map(record => record.performedOn).sort().at(-1) || '';
  const previousWeekLastDate = previousWeekProgress.map(record => record.performedOn).sort().at(-1) || '';
  const planStartDate = workflow.createdAt.slice(0, 10);
  const priorCompletedDate = [latestCompletedDate, previousWeekLastDate].filter(Boolean).sort().at(-1) || '';
  const minimumDate = priorCompletedDate ? addDays(priorCompletedDate, 1) : planStartDate;

  function addDays(date, amount) {
    const value = new Date(`${date}T12:00:00`);
    value.setDate(value.getDate() + amount);
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  }

  const nextDateForWeekday = (weekday, startDate) => {
    const candidate = new Date(`${startDate}T12:00:00`);
    const currentIsoDay = candidate.getDay() || 7;
    candidate.setDate(candidate.getDate() + ((weekday - currentIsoDay + 7) % 7));
    return `${candidate.getFullYear()}-${String(candidate.getMonth() + 1).padStart(2, '0')}-${String(candidate.getDate()).padStart(2, '0')}`;
  };

  const today = new Date();
  const todayDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const [performedOn, setDate] = useState(nextDateForWeekday(day, todayDate < minimumDate ? minimumDate : todayDate));
  const [dateError, setDateError] = useState('');
  const controlsDisabled = busy;

  // Batch mode state for all available days
  const [batchEntries, setBatchEntries] = useState(() =>
    availableDays.map((d, index) => {
      const baseDate = todayDate < minimumDate ? minimumDate : todayDate;
      return {
        day: d.day,
        rpe: 5,
        completed: true,
        pain: false,
        affectedAreas: [],
        performedOn: addDays(baseDate, index),
        noPainConfirmed: true,
      };
    })
  );

  useEffect(() => {
    const currentAvailableDays = workflow.plan.days.filter(planDay => !completedDays.has(planDay.day));
    if (!currentAvailableDays.some(planDay => planDay.day === day) && currentAvailableDays.length > 0) {
      const nextDay = currentAvailableDays[0].day;
      setDay(nextDay);
      setDate(nextDateForWeekday(nextDay, todayDate < minimumDate ? minimumDate : todayDate));
    }
    setBatchEntries(currentAvailableDays.map((d, index) => {
      const baseDate = todayDate < minimumDate ? minimumDate : todayDate;
      return {
        day: d.day,
        rpe: 5,
        completed: true,
        pain: false,
        affectedAreas: [],
        performedOn: addDays(baseDate, index),
        noPainConfirmed: true,
      };
    }));
  }, [progress, day]);

  const updateBatchEntry = (targetDay, key, value) => {
    setBatchEntries(prev => prev.map(item => item.day === targetDay ? { ...item, [key]: value } : item));
  };

  const handleSubmit = async event => {
    event.preventDefault();
    const selectedDate = new Date(`${performedOn}T12:00:00`);
    const selectedIsoDay = selectedDate.getDay() || 7;
    if (performedOn < minimumDate || (!blockPlan && selectedIsoDay !== day)) {
      const sequenceRule = priorCompletedDate
        ? `Choose a date after the last completed session (${priorCompletedDate}).`
        : `Choose a date on or after the schedule start (${planStartDate}).`;
      setDateError(blockPlan ? sequenceRule : `${sequenceRule} The date must be a ${weekdays[day - 1]}.`);
      return;
    }
    if (pain && affectedAreas.length === 0) { setDateError('Select the body area or muscle group affected by pain.'); return; }
    setDateError('');
    if (pain || noPainConfirmed) {
      const saved = await onSave({ day, rpe, completed: !incomplete, pain, affectedAreas: pain ? affectedAreas : [], performedOn });
      if (saved) {
        setIncomplete(false);
        setPain(false);
        setAffectedAreas([]);
        setNoPainConfirmed(false);
        setRpe(5);
      }
    }
  };

  const handleBatchSubmit = async event => {
    event.preventDefault();
    setDateError('');
    for (const entry of batchEntries) {
      if (entry.pain && entry.affectedAreas.length === 0) {
        setDateError(`Day ${entry.day}: Select the body area or muscle group affected by pain.`);
        return;
      }
      await onSave({
        day: entry.day,
        rpe: entry.rpe,
        completed: entry.completed,
        pain: entry.pain,
        affectedAreas: entry.pain ? entry.affectedAreas : [],
        performedOn: entry.performedOn,
      });
    }
  };

  return <>
    {painReported && <div className="fitness-pain-stop" role="alert">
      <strong>Pain recorded</strong>
      <span>Stop any movement that causes pain. The next block avoids exercises targeting the affected area and continues suitable workouts for other areas. Significant, worsening, or persistent pain needs qualified professional guidance.</span>
    </div>}
    {progress.length > 0 && <section className="fitness-session-records" aria-label="Saved session progress">
      <span className="fitness-eyebrow">Session progress</span>
      <ul>{workflow.plan.days.map((planDay, index) => {
        const record = progress.find(item => item.day === planDay.day);
        return <li key={planDay.day} className={record?.completed ? 'is-complete' : ''}>
          <strong>Day {String(index + 1).padStart(2, '0')} · {weekdays[planDay.day - 1]}</strong>
          <span>{record?.completed ? `Completed · ${record.performedOn}` : record ? `Saved · incomplete · ${record.performedOn}` : 'Not recorded yet'}</span>
        </li>;
      })}</ul>
    </section>}
    {availableDays.length > 0 ? (
      <section className="fitness-form-container">
        {batchMode ? (
          <form className="fitness-form fitness-progress-form fitness-reveal" onSubmit={handleBatchSubmit}>
            <span className="fitness-eyebrow">3-month block analysis</span>
            <h3>Record all {availableDays.length} workout days to generate next schedule</h3>
            <p className="fitness-guidance-copy">Fill in performance & effort for all workout days. Recording all days together triggers analysis and generates your next 3-month block.</p>

            {batchEntries.map((entry, idx) => {
              const planDayIndex = workflow.plan.days.findIndex(pd => pd.day === entry.day);
              const planDay = workflow.plan.days[planDayIndex];
              return (
                <div key={entry.day} className="fitness-batch-day-card" style={{ borderBottom: '1px solid var(--fitness-line)', paddingBottom: '16px', marginBottom: '16px' }}>
                  <h4 style={{ color: 'var(--fitness-green)', marginBottom: '8px' }}>
                    Day {String(planDayIndex + 1).padStart(2, '0')} · {planDay?.focus}
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <label>
                      Date
                      <input
                        disabled={controlsDisabled}
                        required
                        type="date"
                        min={minimumDate}
                        value={entry.performedOn}
                        onChange={e => updateBatchEntry(entry.day, 'performedOn', e.target.value)}
                      />
                    </label>
                    <label>
                      Effort RPE (1-10)
                      <input
                        required
                        type="number"
                        min="1"
                        max="10"
                        value={entry.rpe}
                        onChange={e => updateBatchEntry(entry.day, 'rpe', Number(e.target.value))}
                      />
                    </label>
                  </div>
                  <label className="fitness-check" style={{ marginTop: '8px' }}>
                    <input
                      disabled={controlsDisabled}
                      type="checkbox"
                      checked={!entry.completed}
                      onChange={e => updateBatchEntry(entry.day, 'completed', !e.target.checked)}
                    />
                    Did not complete session
                  </label>
                  <label className="fitness-check" style={{ marginTop: '4px' }}>
                    <input
                      disabled={controlsDisabled}
                      type="checkbox"
                      checked={entry.pain}
                      onChange={e => updateBatchEntry(entry.day, 'pain', e.target.checked)}
                    />
                    Experienced pain/discomfort
                  </label>
                  {entry.pain && (
                    <fieldset className="fitness-pain-areas" style={{ marginTop: '8px' }}>
                      <legend>Affected areas:</legend>
                      {bodyAreas.map(area => (
                        <label key={area} className="fitness-check">
                          <input
                            type="checkbox"
                            disabled={controlsDisabled}
                            checked={entry.affectedAreas.includes(area)}
                            onChange={ev => {
                              const updated = ev.target.checked
                                ? [...entry.affectedAreas, area]
                                : entry.affectedAreas.filter(a => a !== area);
                              updateBatchEntry(entry.day, 'affectedAreas', updated);
                            }}
                          />
                          {area}
                        </label>
                      ))}
                    </fieldset>
                  )}
                </div>
              );
            })}

            {dateError && <p role="alert" className="fitness-error fitness-form-feedback">{dateError}</p>}
            {error && <p role="alert" className="fitness-error fitness-form-feedback">{error}</p>}
            {notice && <p role="status" className="fitness-notice fitness-form-feedback">{notice}</p>}
            {working && <p role="status" className="fitness-notice fitness-form-feedback">Saving sessions & analyzing block…</p>}
            <button disabled={controlsDisabled}>
              Save All {availableDays.length} Days & Analyze Block
            </button>
          </form>
        ) : (
          <form className="fitness-form fitness-progress-form fitness-reveal" onSubmit={handleSubmit}>
            <span className="fitness-eyebrow">Keep your plan adaptive</span>
            <h3>Record a session</h3>
            <label>
              {blockPlan ? 'Workout day' : 'Planned weekday'}
              <select disabled={controlsDisabled} value={day} onChange={e => {
                const nextDay = Number(e.target.value);
                setDay(nextDay);
                const earliestDate = todayDate < minimumDate ? minimumDate : todayDate;
                setDate(nextDateForWeekday(nextDay, earliestDate));
                setDateError('');
              }}>
                {availableDays.map(d => {
                  const index = workflow.plan.days.findIndex(planDay => planDay.day === d.day);
                  return <option key={d.day} value={d.day}>Day {String(index + 1).padStart(2, '0')}{blockPlan ? '' : ` · ${weekdays[sessionWeekdays[index] - 1]}`}</option>;
                })}
              </select>
            </label>
            <label>Date<input disabled={controlsDisabled} required type="date" min={minimumDate} value={performedOn} onChange={e => { setDate(e.target.value); setDateError(''); }} /></label>
            {dateError && <p role="alert" className="fitness-error fitness-form-feedback">{dateError}</p>}
            <label>Effort (1 easy – 10 maximum)<input required type="number" min="1" max="10" value={rpe} onChange={e => setRpe(Number(e.target.value))} /></label>
            <label className="fitness-check"><input disabled={controlsDisabled} type="checkbox" checked={incomplete} onChange={e => setIncomplete(e.target.checked)} />Did not complete this session</label>
            <div className={`fitness-pain-alert${pain ? ' is-checked' : ''}`} role="note">
              <label className="fitness-check"><input disabled={controlsDisabled} type="checkbox" checked={pain} onChange={e => {
                const reported = e.target.checked;
                setPain(reported);
                if (reported) setNoPainConfirmed(false);
              }} />I experienced pain or discomfort</label>
              <p>If you experienced pain, record the affected area. The next block will adapt exercises that target it and continue suitable workouts for unaffected areas. If pain is significant, worsening, or persistent, get professional guidance.</p>
              {pain && <fieldset className="fitness-pain-areas"><legend>Where did you feel pain? Select all that apply.</legend>{bodyAreas.map(area => <label key={area} className="fitness-check">
                <input type="checkbox" disabled={controlsDisabled} checked={affectedAreas.includes(area)} onChange={event => setAffectedAreas(current => event.target.checked ? [...current, area] : current.filter(item => item !== area))} />{area.replace(/^./, value => value.toUpperCase())}
              </label>)}</fieldset>}
            </div>
            {!pain && <label className="fitness-check fitness-pain-free-check"><input disabled={controlsDisabled} type="checkbox" checked={noPainConfirmed} onChange={e => setNoPainConfirmed(e.target.checked)} />No pain or discomfort during this session</label>}
            {error && <p role="alert" className="fitness-error fitness-form-feedback">{error}</p>}
            {notice && <p role="status" className="fitness-notice fitness-form-feedback">{notice}</p>}
            {working && <p role="status" className="fitness-notice fitness-form-feedback">Saving your session…</p>}
            {(pain || noPainConfirmed) && <button disabled={controlsDisabled}>Save session</button>}
          </form>
        )}
      </section>
    ) : <p className="fitness-notice fitness-session-complete" role="status">All planned days have been recorded. You can now generate your next schedule.</p>}
  </>;
}
