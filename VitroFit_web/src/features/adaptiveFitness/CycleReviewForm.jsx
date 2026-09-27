import { useState } from 'react';

const equipmentOptions = ['bodyweight', 'dumbbells', 'resistance_band', 'gym'];

export default function CycleReviewForm({ profile, onSubmit, busy, isFirstCycle = true }) {
  const [form, setForm] = useState({
    painOrDiscomfort: 'No current pain or discomfort',
    injuriesOrRestrictions: 'No current injuries or exercise restrictions',
    currentCondition: '',
    goal: profile?.goal ?? 'general_fitness',
    availableWorkoutMinutes: Math.max(100, Math.min(120, profile?.sessionMinutes ?? 120)),
    availableDays: profile?.days ?? [1, 3, 5],
    equipment: profile?.equipment?.length ? profile.equipment : ['bodyweight'],
  });
  const update = (key, value) => setForm(current => ({ ...current, [key]: value }));
  return <form className="fitness-form fitness-cycle-review" onSubmit={event => { event.preventDefault(); onSubmit(form); }}>
    <span className="fitness-eyebrow">Three-month cycle check-in</span>
    <h3>Review your current condition</h3>
    <p>These answers guide the next 3-month schedule. If you have significant, worsening, or persistent pain, seek qualified professional guidance before training.</p>
    <label>Pain or discomfort<textarea required maxLength="300" value={form.painOrDiscomfort} onChange={event => update('painOrDiscomfort', event.target.value)} /></label>
    <label>Injuries or exercise restrictions<textarea required maxLength="300" value={form.injuriesOrRestrictions} onChange={event => update('injuriesOrRestrictions', event.target.value)} /></label>
    <label>How are you feeling now? Describe your current condition.<textarea required minLength="2" maxLength="500" value={form.currentCondition} onChange={event => update('currentCondition', event.target.value)} /></label>
    <label>Current goal<select value={form.goal} onChange={event => update('goal', event.target.value)}>
      <option value="weight_loss">Weight loss</option><option value="muscle_building">Build muscle</option>
      <option value="general_fitness">General fitness</option><option value="strength">Build strength</option><option value="endurance">Improve endurance</option>
    </select></label>
    <label>Available workout minutes (100–120)<input required type="number" min="100" max="120" value={form.availableWorkoutMinutes} onChange={event => update('availableWorkoutMinutes', Number(event.target.value))} /></label>
    <fieldset><legend>Available workout days (choose 3 or 4)</legend>{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => <label className="fitness-check" key={day}>
      <input type="checkbox" checked={form.availableDays.includes(index + 1)} disabled={(!form.availableDays.includes(index + 1) && form.availableDays.length >= 4) || (form.availableDays.includes(index + 1) && form.availableDays.length <= 3)} onChange={event => update('availableDays', event.target.checked ? [...form.availableDays, index + 1] : form.availableDays.filter(value => value !== index + 1))} />{day}
    </label>)}</fieldset>
    <fieldset><legend>Available equipment</legend>{equipmentOptions.map(item => <label className="fitness-check" key={item}>
      <input type="checkbox" checked={form.equipment.includes(item)} onChange={event => update('equipment', event.target.checked
        ? [...form.equipment, item] : form.equipment.filter(value => value !== item))} />{item.replace('_', ' ')}
    </label>)}</fieldset>
    <button disabled={busy || !form.currentCondition.trim() || form.equipment.length === 0}>
      {isFirstCycle ? 'Save Review & Generate 3-Month Schedule' : 'Save Review & Generate Next 3-Month Schedule'}
    </button>
  </form>;
}
