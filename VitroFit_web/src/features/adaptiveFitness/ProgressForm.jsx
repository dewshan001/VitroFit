import { useState } from 'react';

export default function ProgressForm({ workflow, onSave, busy }) {
  const [day, setDay] = useState(workflow.plan.days[0].day);
  const [rpe, setRpe] = useState(5);
  const [completed, setCompleted] = useState(true);
  const [pain, setPain] = useState(false);
  const [noPainConfirmed, setNoPainConfirmed] = useState(false);
  const [performedOn, setDate] = useState(new Date().toISOString().slice(0, 10));
  const handleSubmit = event => {
    event.preventDefault();
    if (pain || noPainConfirmed) onSave({ day, rpe, completed, pain, performedOn });
  };
  return <form className="fitness-form fitness-progress-form fitness-reveal" onSubmit={handleSubmit}>
    <span className="fitness-eyebrow">Keep your plan adaptive</span><h3>Record a session</h3><label>Planned weekday<select value={day} onChange={e => setDay(Number(e.target.value))}>
      {workflow.plan.days.map(d => <option key={d.day} value={d.day}>Day {d.day} (Monday = 1)</option>)}</select></label>
    <label>Date<input required type="date" value={performedOn} onChange={e => setDate(e.target.value)} /></label>
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
    {(pain || noPainConfirmed) && <button disabled={busy}>Save session</button>}
  </form>;
}
