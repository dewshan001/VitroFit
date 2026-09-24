import { useState } from 'react';

const defaults = { age: 25, heightCm: 170, weightKg: 70, goal: 'general_fitness', days: [1, 3, 5], sessionMinutes: 30, equipment: ['bodyweight'], reviewRequired: false };
const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function FitnessProfileForm({ initial, onSave, busy, createSchedule = false, onCancel }) {
  const [form, setForm] = useState(initial || defaults);
  const [confirmed, setConfirmed] = useState(false);
  const field = (key, value) => setForm(old => ({ ...old, [key]: value }));
  return <form className="fitness-form fitness-profile-form fitness-reveal" onSubmit={event => { event.preventDefault(); onSave(form); }}>
    <span className="fitness-eyebrow">Start with the essentials</span>
    <h2>Your beginner fitness profile</h2>
    <p>For adult beginners. Confirm equipment is available at your gym before selecting it.</p>
    <div className="fitness-fields">
      {[['age', 'Age', 18, 80], ['heightCm', 'Height (cm)', 100, 250], ['weightKg', 'Weight (kg)', 30, 300], ['sessionMinutes', 'Session minutes', 20, 60]].map(([key, label, min, max]) =>
        <label key={key}>{label}<input required type="number" min={min} max={max} step={key === 'weightKg' ? '0.1' : '1'} value={form[key]} onChange={e => field(key, Number(e.target.value))} /></label>)}
      <label>Your training target<select value={form.goal} onChange={e => field('goal', e.target.value)}>
        <option value="weight_loss">Weight loss</option><option value="muscle_building">Build muscle</option>
        <option value="general_fitness">General fitness</option><option value="strength">Build strength</option><option value="endurance">Improve endurance</option>
      </select></label>
    </div>
    <fieldset><legend>Training days (choose 1–3)</legend>{names.map((name, index) => <label className="fitness-check" key={name}>
      <input type="checkbox" checked={form.days.includes(index + 1)} disabled={!form.days.includes(index + 1) && form.days.length >= 3}
        onChange={e => field('days', e.target.checked ? [...form.days, index + 1] : form.days.filter(d => d !== index + 1))} />{name}</label>)}</fieldset>
    <fieldset><legend>Confirmed equipment</legend>{['dumbbells', 'resistance_band'].map(item => <label className="fitness-check" key={item}>
      <input type="checkbox" checked={form.equipment.includes(item)} onChange={e => field('equipment', e.target.checked ? [...form.equipment, item] : form.equipment.filter(x => x !== item))} />{item.replaceAll('_', ' ')}</label>)}</fieldset>
    <fieldset><legend>Self-training health check</legend>
      <p>Do any of these apply: chest discomfort, fainting, or unusual breathlessness during activity; a medical condition not cleared or controlled for exercise; recent surgery or injury; pregnancy-related exercise restrictions; or a clinician advised you to avoid exercise or seek guidance?</p>
      <label className="fitness-check"><input type="checkbox" checked={form.reviewRequired} onChange={e => field('reviewRequired', e.target.checked)} />Yes, one or more applies. Pause my self-guided plan for professional guidance.</label>
    </fieldset>
    <label className="fitness-check"><input required type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />I reviewed my answers and understand this is not medical clearance.</label>
    <button disabled={busy || form.days.length === 0 || !confirmed}>
      {createSchedule ? 'Save profile and create week 1' : 'Save profile'}
    </button>
    {onCancel && <button type="button" disabled={busy} onClick={onCancel}>Cancel</button>}
  </form>;
}
