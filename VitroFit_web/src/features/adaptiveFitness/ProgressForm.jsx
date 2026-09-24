import { useState } from 'react';

export default function ProgressForm({ workflow, onSave, busy }) {
  const [day, setDay] = useState(workflow.plan.days[0].day);
  const [rpe, setRpe] = useState(5);
  const [completed, setCompleted] = useState(true);
  const [pain, setPain] = useState(false);
  const [performedOn, setDate] = useState(new Date().toISOString().slice(0, 10));
  return <form className="fitness-form fitness-progress-form fitness-reveal" onSubmit={e => { e.preventDefault(); onSave({ day, rpe, completed, pain, performedOn }); }}>
    <span className="fitness-eyebrow">Keep your plan adaptive</span><h3>Record a session</h3><label>Planned weekday<select value={day} onChange={e => setDay(Number(e.target.value))}>
      {workflow.plan.days.map(d => <option key={d.day} value={d.day}>Day {d.day} (Monday = 1)</option>)}</select></label>
    <label>Date<input required type="date" value={performedOn} onChange={e => setDate(e.target.value)} /></label>
    <label>Effort (1 easy – 10 maximum)<input required type="number" min="1" max="10" value={rpe} onChange={e => setRpe(Number(e.target.value))} /></label>
    <label className="fitness-check"><input type="checkbox" checked={completed} onChange={e => setCompleted(e.target.checked)} />Completed</label>
    <label className="fitness-check"><input type="checkbox" checked={pain} onChange={e => setPain(e.target.checked)} />Pain or discomfort reported</label>
    <button disabled={busy}>Save session</button>
  </form>;
}
