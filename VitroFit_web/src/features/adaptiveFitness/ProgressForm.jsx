import { useEffect, useState } from 'react';

export default function ProgressForm({ workflow, progress = [], previousWeekProgress = [], onSave, busy, error, notice, working }) {
  const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const sessionWeekdays = workflow.plan.days.map(d => d.day);
  const completedRecords = progress.filter(record => record.completed);
  const completedDays = new Set(completedRecords.map(record => record.day));
  const availableDays = workflow.plan.days.filter(planDay => !completedDays.has(planDay.day));
  const initialDay = availableDays[0]?.day ?? workflow.plan.days[0].day;
  const [day, setDay] = useState(initialDay);
  const [rpe, setRpe] = useState(5);
  const [completed, setCompleted] = useState(true);
  const [pain, setPain] = useState(false);
  const [noPainConfirmed, setNoPainConfirmed] = useState(false);
  const latestCompletedDate = completedRecords.map(record => record.performedOn).sort().at(-1) || '';
  const previousWeekLastDate = previousWeekProgress.filter(record => record.completed)
    .map(record => record.performedOn).sort().at(-1) || '';
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
  useEffect(() => {
    if (!availableDays.some(planDay => planDay.day === day) && availableDays.length > 0) {
      const nextDay = availableDays[0].day;
      setDay(nextDay);
      setDate(nextDateForWeekday(nextDay, todayDate < minimumDate ? minimumDate : todayDate));
    }
  }, [progress, day, minimumDate, todayDate, availableDays]);
  const handleSubmit = event => {
    event.preventDefault();
    const selectedDate = new Date(`${performedOn}T12:00:00`);
    const selectedIsoDay = selectedDate.getDay() || 7;
    if (performedOn < minimumDate || selectedIsoDay !== day) {
      const sequenceRule = priorCompletedDate
        ? `Choose a date after the last completed session (${priorCompletedDate}).`
        : `Choose a date on or after the schedule start (${planStartDate}).`;
      setDateError(`${sequenceRule} The date must be a ${weekdays[day - 1]}.`);
      return;
    }
    setDateError('');
    if (pain || noPainConfirmed) {
      onSave({ day, rpe, completed, pain, performedOn });
      setNoPainConfirmed(false);
    }
  };
  return <>
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
    {availableDays.length > 0 ? <form className="fitness-form fitness-progress-form fitness-reveal" onSubmit={handleSubmit}>
    <span className="fitness-eyebrow">Keep your plan adaptive</span><h3>Record a session</h3><label>Planned weekday<select value={day} onChange={e => {
      const nextDay = Number(e.target.value);
      setDay(nextDay);
      const earliestDate = todayDate < minimumDate ? minimumDate : todayDate;
      setDate(nextDateForWeekday(nextDay, earliestDate));
      setDateError('');
    }}>
      {availableDays.map(d => {
        const index = workflow.plan.days.findIndex(planDay => planDay.day === d.day);
        return <option key={d.day} value={d.day}>Day {String(index + 1).padStart(2, '0')} · {weekdays[sessionWeekdays[index] - 1]}</option>;
      })}</select></label>
    <label>Date<input required type="date" min={minimumDate} value={performedOn} onChange={e => { setDate(e.target.value); setDateError(''); }} /></label>
    {dateError && <p role="alert" className="fitness-error fitness-form-feedback">{dateError}</p>}
    <label>Effort (1 easy – 10 maximum)<input required type="number" min="1" max="10" value={rpe} onChange={e => setRpe(Number(e.target.value))} /></label>
    <label className="fitness-check"><input type="checkbox" checked={completed} onChange={e => setCompleted(e.target.checked)} />Completed</label>
    <div className={`fitness-pain-alert${pain ? ' is-checked' : ''}`} role="note">
      <label className="fitness-check"><input type="checkbox" checked={pain} onChange={e => {
        const reported = e.target.checked;
        setPain(reported);
        if (reported) setNoPainConfirmed(false);
      }} />I experienced pain or discomfort</label>
      <p>If you experienced pain or felt unwell, select this and stop exercising until you have appropriate guidance. If you had no pain, confirm that below to enable saving the session.</p>
    </div>
    {!pain && <label className="fitness-check fitness-pain-free-check"><input type="checkbox" checked={noPainConfirmed} onChange={e => setNoPainConfirmed(e.target.checked)} />No pain or discomfort during this session</label>}
    {error && <p role="alert" className="fitness-error fitness-form-feedback">{error}</p>}
    {notice && <p role="status" className="fitness-notice fitness-form-feedback">{notice}</p>}
    {working && <p role="status" className="fitness-notice fitness-form-feedback">Saving your session…</p>}
    {(pain || noPainConfirmed) && <button disabled={busy}>Save session</button>}
    </form> : <p className="fitness-notice fitness-session-complete" role="status">All planned days have been recorded as complete.</p>}
  </>;
}
