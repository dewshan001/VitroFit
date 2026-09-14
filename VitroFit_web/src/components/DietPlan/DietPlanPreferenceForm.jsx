import { useState } from 'react';

const ACTIVITY_OPTIONS = [
  { value: 'sedentary', label: 'Sedentary (little exercise)' },
  { value: 'light', label: 'Lightly active (1–3 days / week)' },
  { value: 'moderate', label: 'Moderately active (3–5 days / week)' },
  { value: 'active', label: 'Very active (6–7 days / week)' },
];

const GOAL_OPTIONS = [
  { value: 'weight loss', label: 'Weight Loss' },
  { value: 'muscle gain', label: 'Muscle Gain' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'endurance', label: 'Endurance' },
];

const RESTRICTIONS = [
  'vegetarian',
  'vegan',
  'halal',
  'dairy-free',
  'gluten-free',
  'peanut allergy',
  'lactose-intolerant',
];

const MEAL_FREQUENCIES = [
  { value: '3Meals', label: '3 meals / day' },
  { value: '4Meals', label: '4 meals / day' },
  { value: '5Meals', label: '5 meals / day' },
  { value: 'intermittent', label: 'Intermittent fasting (16:8)' },
];

/**
 * Custom number stepper (▲ / ▼) styled to match the app's dropdown arrows
 * instead of the browser's native white up/down spin box.
 */
function NumberStepper({ value, onChange, min, max, label, placeholder }) {
  const step = (dir) => {
    const current = Number(value) || 0;
    let next = current + dir;
    if (min !== undefined && next < min) next = min;
    if (max !== undefined && next > max) next = max;
    if (next !== current) onChange(next);
  };

  return (
    <div className="dp-stepper">
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
        placeholder={placeholder}
        aria-label={label}
      />
      <div className="dp-stepper-buttons">
        <button
          type="button"
          className="dp-stepper-btn"
          onClick={() => step(1)}
          aria-label={`Increase ${label}`}
        >
          <svg width="10" height="6" viewBox="0 0 12 8" fill="none">
            <path d="M1 6l5-5 5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          </svg>
        </button>
        <button
          type="button"
          className="dp-stepper-btn"
          onClick={() => step(-1)}
          aria-label={`Decrease ${label}`}
        >
          <svg width="10" height="6" viewBox="0 0 12 8" fill="none">
            <path d="M1 2l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          </svg>
        </button>
      </div>
    </div>
  );
}

/**
 * Diet plan preference & goals form (frontend only).
 *
 * Collects the personal details and goals the Agentic AI agent will later use
 * to generate an individualised meal plan. Kept separate from the results view
 * for clean future integration.
 */
export default function DietPlanPreferenceForm({ initialPrefs, onSubmit }) {
  const [form, setForm] = useState({
    age: initialPrefs?.age ?? 25,
    gender: initialPrefs?.gender ?? 'male',
    heightCm: initialPrefs?.heightCm ?? 175,
    weightKg: initialPrefs?.weightKg ?? 70,
    activityLevel: initialPrefs?.activityLevel ?? 'moderate',
    goal: initialPrefs?.goal ?? 'maintenance',
    mealFrequency: initialPrefs?.mealFrequency ?? '3Meals',
    restrictions: initialPrefs?.restrictions ?? [],
    dislikes: initialPrefs?.dislikes ?? '',
  });
  const [errors, setErrors] = useState({});

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const toggleRestriction = (value) => {
    setForm((prev) => ({
      ...prev,
      restrictions: prev.restrictions.includes(value)
        ? prev.restrictions.filter((r) => r !== value)
        : [...prev.restrictions, value],
    }));
  };

  const validate = () => {
    const e = {};
    if (!form.age || form.age < 10 || form.age > 100) e.age = 'Enter an age between 10 and 100.';
    if (!form.heightCm || form.heightCm < 100 || form.heightCm > 260) e.heightCm = 'Enter a height between 100 and 260 cm.';
    if (!form.weightKg || form.weightKg < 30 || form.weightKg > 250) e.weightKg = 'Enter a weight between 30 and 250 kg.';
    if (!form.gender) e.gender = 'Select your gender.';
    if (!form.activityLevel) e.activityLevel = 'Select your activity level.';
    if (!form.goal) e.goal = 'Select your primary goal.';
    if (!form.mealFrequency) e.mealFrequency = 'Select a meal frequency.';
    return e;
  };

  const handleSubmit = (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).some((k) => e[k])) return;
    onSubmit({ ...form });
  };

  return (
    <form className="dp-form dp-fade-up" onSubmit={handleSubmit} noValidate>
      <div className="dp-form-head">
        <h2 className="dp-form-title">Tell Us About You</h2>
        <p className="dp-form-sub">
          We reuse your profile where available and fill in the rest below. All
          fields help tailor your plan.
        </p>
      </div>

      <div className="dp-form-group">
        <h3 className="dp-form-group-title">Personal Details</h3>
        <div className="dp-field-grid">
          <label className={`dp-field${errors.age ? ' dp-field-error' : ''}`}>
            <span className="dp-field-label">Age</span>
            <NumberStepper
              value={form.age}
              min={10}
              max={100}
              label="Age"
              placeholder="e.g. 25"
              onChange={(v) => setField('age', v)}
            />
            {errors.age && <span className="dp-field-err-text">{errors.age}</span>}
          </label>

          <label className={`dp-field${errors.gender ? ' dp-field-error' : ''}`}>
            <span className="dp-field-label">Gender</span>
            <select value={form.gender} onChange={(e) => setField('gender', e.target.value)}>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label className={`dp-field${errors.heightCm ? ' dp-field-error' : ''}`}>
            <span className="dp-field-label">Height (cm)</span>
            <NumberStepper
              value={form.heightCm}
              min={100}
              max={260}
              label="Height (cm)"
              placeholder="e.g. 175"
              onChange={(v) => setField('heightCm', v)}
            />
            {errors.heightCm && <span className="dp-field-err-text">{errors.heightCm}</span>}
          </label>

          <label className={`dp-field${errors.weightKg ? ' dp-field-error' : ''}`}>
            <span className="dp-field-label">Weight (kg)</span>
            <NumberStepper
              value={form.weightKg}
              min={30}
              max={250}
              label="Weight (kg)"
              placeholder="e.g. 70"
              onChange={(v) => setField('weightKg', v)}
            />
            {errors.weightKg && <span className="dp-field-err-text">{errors.weightKg}</span>}
          </label>

          <label className={`dp-field dp-field-wide${errors.activityLevel ? ' dp-field-error' : ''}`}>
            <span className="dp-field-label">Activity Level</span>
            <select
              value={form.activityLevel}
              onChange={(e) => setField('activityLevel', e.target.value)}
            >
              {ACTIVITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            {errors.activityLevel && <span className="dp-field-err-text">{errors.activityLevel}</span>}
          </label>
        </div>
      </div>

      <div className="dp-form-group">
        <h3 className="dp-form-group-title">Your Primary Goal</h3>
        <div className="dp-chip-row">
          {GOAL_OPTIONS.map((g) => (
            <button
              type="button"
              key={g.value}
              className={`dp-chip${form.goal === g.value ? ' active' : ''}`}
              onClick={() => setField('goal', g.value)}
            >
              {g.label}
            </button>
          ))}
        </div>
        {errors.goal && <span className="dp-field-err-text">{errors.goal}</span>}
      </div>

      <div className="dp-form-group">
        <h3 className="dp-form-group-title">Dietary Preferences</h3>
        <div className="dp-chip-row">
          {RESTRICTIONS.map((r) => (
            <button
              type="button"
              key={r}
              className={`dp-chip${form.restrictions.includes(r) ? ' active' : ''}`}
              onClick={() => toggleRestriction(r)}
            >
              {r}
            </button>
          ))}
        </div>
        <p className="dp-field-hint">Select any that apply (optional).</p>
      </div>

      <div className="dp-form-group">
        <h3 className="dp-form-group-title">Meal Frequency</h3>
        <div className="dp-chip-row">
          {MEAL_FREQUENCIES.map((m) => (
            <button
              type="button"
              key={m.value}
              className={`dp-chip${form.mealFrequency === m.value ? ' active' : ''}`}
              onClick={() => setField('mealFrequency', m.value)}
            >
              {m.label}
            </button>
          ))}
        </div>
        {errors.mealFrequency && <span className="dp-field-err-text">{errors.mealFrequency}</span>}
      </div>

      <div className="dp-form-group">
        <h3 className="dp-form-group-title">Anything We Should Avoid?</h3>
        <label className="dp-field">
          <span className="dp-field-label">Dislikes (optional)</span>
          <textarea
            value={form.dislikes}
            onChange={(e) => setField('dislikes', e.target.value)}
            placeholder="e.g. I don't like mushrooms or cinnamon, prefer mild spice levels..."
            rows={3}
          />
        </label>
      </div>

      <div className="dp-form-actions">
        <button type="submit" className="btn-primary">
          Generate My Plan
        </button>
      </div>
    </form>
  );
}