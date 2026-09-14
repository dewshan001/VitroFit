import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import DietPlanPreferenceForm from './DietPlanPreferenceForm';
import DietPlanResult from './DietPlanResult';
import './DietPlan.css';

/* ──────────────────────────────────────────────
   MOCK DATA  (replace with Agentic AI backend later)
   ────────────────────────────────────────────── */

// Mock "menu" pools keyed by category so generated plans look realistic.
const FOOD_POOL = {
  protein: [
    { name: 'Grilled Chicken Breast', unit: '150g', kcal: 248 },
    { name: 'Baked Salmon Fillet', unit: '140g', kcal: 290 },
    { name: 'Lean Beef Sirloin', unit: '150g', kcal: 330 },
    { name: 'Tofu', unit: '200g', kcal: 190 },
    { name: 'Chickpeas', unit: '180g', kcal: 320 },
    { name: 'Egg Whites', unit: '160g', kcal: 85 },
    { name: 'Turkey Breast', unit: '160g', kcal: 220 },
  ],
  carbohydrate: [
    { name: 'Brown Rice', unit: '150g cooked', kcal: 216 },
    { name: 'Sweet Potato', unit: '200g', kcal: 180 },
    { name: 'Wholegrain Pasta', unit: '120g cooked', kcal: 220 },
    { name: 'Quinoa', unit: '140g cooked', kcal: 230 },
    { name: 'Oats', unit: '60g dry', kcal: 220 },
    { name: 'Wholewheat Bread', unit: '2 slices', kcal: 160 },
  ],
  vegetable: [
    { name: 'Fresh Salad Greens', unit: '150g', kcal: 30 },
    { name: 'Steamed Broccoli', unit: '150g', kcal: 55 },
    { name: 'Roasted Vegetables', unit: '200g', kcal: 90 },
    { name: 'Spinach & Kale', unit: '120g', kcal: 34 },
    { name: 'Mixed Veggie Bowl', unit: '180g', kcal: 80 },
  ],
  fruit: [
    { name: 'Banana', unit: '1 medium', kcal: 105 },
    { name: 'Apple', unit: '1 medium', kcal: 95 },
    { name: 'Blueberries', unit: '100g', kcal: 57 },
    { name: 'Orange', unit: '1 medium', kcal: 62 },
  ],
  dairy: [
    { name: 'Greek Yoghurt', unit: '150g', kcal: 130 },
    { name: 'Low-fat Milk', unit: '250ml', kcal: 120 },
    { name: 'Cottage Cheese', unit: '120g', kcal: 95 },
  ],
  fat: [
    { name: 'Extra Virgin Olive Oil', unit: '1 tbsp', kcal: 120 },
    { name: 'Avocado', unit: '75g', kcal: 120 },
    { name: 'Almonds', unit: '28g', kcal: 164 },
    { name: 'Peanut Butter', unit: '1 tbsp', kcal: 94 },
  ],
  snack: [
    { name: 'Mixed Nuts', unit: '30g', kcal: 180 },
    { name: 'Protein Shake', unit: '1 scoop', kcal: 120 },
    { name: 'Rice Cakes with Cottage Cheese', unit: '2 pieces', kcal: 130 },
    { name: 'Carrot & Hummus', unit: '1 serving', kcal: 140 },
  ],
};

// Real hero for the page banner.
const HERO_IMG =
  'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=2000&q=80';

const ACTIVITY_FACTORS = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
};

export default function DietPlan() {
  const { auth, getFullName } = useAuth();
  const user = auth?.user ?? {};

  // phase: 'empty' | 'form' | 'loading' | 'result'
  const [phase, setPhase] = useState('empty');
  const [plan, setPlan] = useState(null);

  // Prefill from existing profile where available (goal + level).
  const initialPrefs = {
    age: user.age ?? 25,
    gender: user.gender ?? 'male',
    heightCm: user.heightCm ?? 175,
    weightKg: user.weightKg ?? 70,
    activityLevel: mapActivityFromLevel(user.level) ?? 'moderate',
    goal: user.goal ?? 'maintenance',
    mealFrequency: '3Meals',
    restrictions: [],
    dislikes: user.dislikes ?? '',
  };

  // Remembers the most recently used preferences for Regenerate.
  const [lastPrefs, setLastPrefs] = useState(initialPrefs);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add('visible');
        });
      },
      { threshold: 0.1 }
    );
    document
      .querySelectorAll('.dp-fade-up')
      .forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [phase]);
/**
   * Simulated "Generating..." step with a timeout to make the loader visible.
   * Later this becomes a real call to the Agentic AI backend generating an
   * individualised meal plan from the supplied preferences.
   */
  const handleGenerate = (prefs) => {
    setPhase('loading');

    // TODO: connect to Agentic AI backend.
    // Expected request shape:
    //   { userId, goal, age, gender, heightCm, weightKg,
    //     activityLevel, mealFrequency, restrictions[], dislikes }
    // Expected response shape:
    //   { totalCalories, macros: { protein, carbs, fat },
    //     meals: [{ type, label, items: [{ name, portion, calories, macros }] }] }
    setTimeout(() => {
      setPlan(generateMockPlan(prefs));
      setPhase('result');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 1600);
  };

  const handleEdit = () => setPhase('form');

  const runGenerate = (prefs) => {
    setLastPrefs(prefs);
    handleGenerate(prefs);
  };

  const startForm = () => setPhase('form');

  return (
    <div className="diet-plan-page">
      <section className="dp-hero">
        <img src={HERO_IMG} alt="Healthy food bowl" className="dp-hero-img" />
        <div className="dp-hero-overlay" />
        <div className="dp-hero-accent-shape" />
        <div className="container dp-hero-content">
          <div className="dp-breadcrumb dp-fade-up">
            Home &gt; <span>Diet Plans</span>
          </div>
          <div className="dp-hero-eyebrow dp-fade-up dp-d1">
            <div className="dp-hero-eyebrow-line" />
            <span className="dp-hero-eyebrow-text">VitroFit AI Nutrition</span>
          </div>
          <h1 className="dp-hero-title dp-fade-up dp-d2">
            <span className="outline-text">PERSONALISED</span> DIET<br />
            PLANS FOR YOUR GOALS
          </h1>
          <p className="dp-hero-sub dp-fade-up dp-d3">
            Tell us about your body, goals, and preferences to get
            {getFullName() ? ` a plan tailored for ${getFullName()}` : ' a tailored'} plan —
            built meal by meal with realistic portions and macros.
          </p>
        </div>
      </section>

      <section className="dp-section">
        <div className="container">
          {phase === 'empty' && <DietPlanResult state="empty" onGenerate={startForm} />}
          {phase === 'form' && (
            <DietPlanPreferenceForm initialPrefs={initialPrefs} onSubmit={runGenerate} />
          )}
          {phase === 'loading' && <DietPlanResult state="loading" />}
          {phase === 'result' && plan && (
            <DietPlanResult
              state="result"
              plan={plan}
              onEdit={handleEdit}
              onRegenerate={() => runGenerate(lastPrefs)}
            />
          )}
        </div>
      </section>

      <section className="dp-cta">
        <img
          src="https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=2000&q=80"
          alt="Healthy meal ingredients"
          className="dp-cta-img"
        />
        <div className="dp-cta-overlay" />
        <div className="dp-cta-accent-shape" />
        <div className="container dp-cta-content dp-fade-up">
          <h2 className="dp-cta-title">
            <span className="outline-text">EAT SMART</span>, TRAIN
            <br />
            WITHOUT LIMITS
          </h2>
          <p className="dp-cta-desc">
            Combine your personalised meal plan with your workout schedule and
            partner gyms on VitroFit — sustain your energy wherever you train.
          </p>
          <div className="mt-4">
            <button className="btn-primary" onClick={startForm}>
              Build My Plan
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
/* ──────────────────────────────────────────────
   HELPERS  (mock generation logic)
────────────────────────────────────────────── */

/** Map an existing profile `level` to an activity factor key (reuse profile data). */
function mapActivityFromLevel(level) {
  if (!level) return null;
  const l = String(level).toLowerCase();
  if (l.includes('beginner') || l.includes('lightly')) return 'light';
  if (l.includes('advanced') || l.includes('highly')) return 'active';
  if (l.includes('intermediate')) return 'moderate';
  return null;
}

function pick(arr) {
  if (!arr.length) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

// Approx macros (grams) per 100 kcal, keyed by goal — purely illustrative.
const MACRO_SPLIT = {
  'weight loss': { p: 12, c: 9, f: 3 },
  'muscle gain': { p: 14, c: 11, f: 3 },
  maintenance:   { p: 11, c: 13, f: 3 },
  endurance:     { p: 11, c: 15, f: 3 },
};

/** Rough per-item macro estimate from calories + goal split. */
function macrosFor(kcal, goal) {
  const split = MACRO_SPLIT[goal] ?? MACRO_SPLIT['maintenance'];
  return {
    protein: Math.round((split.p / 100) * kcal),
    carbs: Math.round((split.c / 100) * kcal),
    fat: Math.round((split.f / 100) * kcal),
  };
}

/** Daily macro totals (grams) derived from the calorie target. */
function splitMacros(target, goal) {
  const split = MACRO_SPLIT[goal] ?? MACRO_SPLIT['maintenance'];
  return {
    protein: Math.round((split.p / 100) * target),
    carbs: Math.round((split.c / 100) * target),
    fat: Math.round((split.f / 100) * target),
  };
}

/**
 * Build a deterministic-looking mock plan from the supplied preferences.
 * This simulates the future Agentic AI response until wired to the backend.
 */
function generateMockPlan(prefs) {
  const { gender, age, heightCm, weightKg, activityLevel, goal, mealFrequency } = prefs;

  // Naive BMR (Mifflin-St Jeor) + activity multiplier to derive a target.
  const base =
    gender === 'female'
      ? 10 * weightKg + 6.25 * heightCm - 5 * age - 161
      : 10 * weightKg + 6.25 * heightCm - 5 * age + 5;
  const factor = ACTIVITY_FACTORS[activityLevel] ?? 1.55;
  let target = Math.round(base * factor);
  if (goal === 'weight loss') target = Math.round(target * 0.85);
  else if (goal === 'muscle gain') target = Math.round(target * 1.12);
  else if (goal === 'endurance') target = Math.round(target * 1.05);

  const vegan = prefs.restrictions.includes('vegan');
  const vegetarian = prefs.restrictions.includes('vegetarian');

  // Pick a plant-based protein when vegan/vegetarian.
  const proteinPool = (vegan || vegetarian)
    ? FOOD_POOL.protein.filter((x) => x.name === 'Tofu' || x.name === 'Chickpeas')
    : FOOD_POOL.protein;

  function addItem(food) {
    if (!food) return null;
    return { name: food.name, portion: food.unit, calories: food.kcal, macros: macrosFor(food.kcal, goal) };
  }

  function buildMeal(label, count) {
    const items = [];
    const foods = [
      pick(proteinPool),
      pick(FOOD_POOL.carbohydrate),
      pick(FOOD_POOL.vegetable),
      pick([...FOOD_POOL.fruit, ...FOOD_POOL.fat, ...FOOD_POOL.dairy]),
    ];
    for (let i = 0; i < count && foods[i]; i += 1) items.push(addItem(foods[i]));
    return { type: label.toLowerCase(), label, items };
  }

  let meals;
  if (mealFrequency === 'intermittent') {
    meals = [
      { type: 'breakfast', label: 'Breakfast (12:00 PM)', items: [
          addItem(pick(proteinPool)),
          addItem(pick(FOOD_POOL.carbohydrate)),
          addItem(pick(FOOD_POOL.vegetable)),
        ].filter(Boolean) },
      { type: 'lunch', label: 'Lunch (3:00 PM)', items: [
        addItem(pick(proteinPool)),
        addItem(pick(FOOD_POOL.carbohydrate)),
        addItem(pick(FOOD_POOL.vegetable)),
        addItem(pick(FOOD_POOL.fat)),
      ].filter(Boolean) },
      { type: 'dinner', label: 'Dinner (7:00 PM)', items: [
        addItem(pick(proteinPool)),
        addItem(pick(FOOD_POOL.carbohydrate)),
        addItem(pick(FOOD_POOL.vegetable)),
      ].filter(Boolean) },
    ];
  } else if (mealFrequency === '5Meals') {
    meals = [
      buildMeal('Breakfast', 3),
      { type: 'snack', label: 'Morning Snack', items: [addItem(pick(FOOD_POOL.fruit))].filter(Boolean) },
      buildMeal('Lunch', 4),
      { type: 'snack', label: 'Afternoon Snack', items: [addItem(pick(FOOD_POOL.snack))].filter(Boolean) },
      buildMeal('Dinner', 4),
    ];
  } else if (mealFrequency === '4Meals') {
    meals = [
      buildMeal('Breakfast', 3),
      buildMeal('Lunch', 4),
      buildMeal('Snack', 1),
      buildMeal('Dinner', 4),
    ];
  } else {
    meals = [
      buildMeal('Breakfast', 3),
      buildMeal('Lunch', 4),
      buildMeal('Snack', 1),
      buildMeal('Dinner', 4),
    ];
  }

  return {
    totalCalories: target,
    macros: splitMacros(target, goal),
    meals,
  };
}