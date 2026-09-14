const MEAL_ICONS = {
  breakfast: '🍳',
  lunch: '🥗',
  dinner: '🍽️',
  snack: '🍎',
};

const MEAL_FALLBACK_ICON = '🍽️';

/**
 * Diet plan results/display component.
 *
 * Handles three states:
 *  - empty:  no plan generated yet (call to action to build one)
 *  - loading: simulated skeleton while the AI "generates" the plan
 *  - result: the generated meal plan broken down by meal with macros & totals
 */
export default function DietPlanResult({ state, plan, onGenerate, onEdit, onRegenerate }) {
  if (state === 'empty') {
    return (
      <div className="dp-empty dp-fade-up">
        <div className="dp-empty-icon">🍽️</div>
        <h2 className="dp-empty-title">No Diet Plan Yet</h2>
        <p className="dp-empty-desc">
          Answer a few quick questions about your body, goals, and dietary
          preferences and we'll generate a personalised plan for you.
        </p>
        <button className="btn-primary" onClick={onGenerate}>
          Build My Diet Plan
        </button>
      </div>
    );
  }

  if (state === 'loading') {
    return (
      <div className="dp-loading dp-fade-up">
        <div className="dp-loading-top">
          <span className="dp-loader" />
          <h3 className="dp-loading-title">Generating your diet plan…</h3>
          <p className="dp-loading-desc">
            {simulateLoadingText()}
          </p>
        </div>
        <div className="dp-skeleton-list">
          {[0, 1, 2, 3].map((m) => (
            <div className="dp-skeleton-meal" key={m}>
              <div className="dp-skeleton-label shimmer" />
              <div className="dp-skeleton-rows">
                {[0, 1, 2].map((r) => (
                  <div className="dp-skeleton-line shimmer" key={r} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // state === 'result'
  const totalCalories = plan?.totalCalories ?? 0;
  const macros = plan?.macros ?? { protein: 0, carbs: 0, fat: 0 };
  const meals = plan?.meals ?? [];

  const mealCalories = (meal) =>
    (meal.items || []).reduce((sum, item) => sum + (item.calories || 0), 0);
  const icon = (type) => MEAL_ICONS[type?.toLowerCase()] || MEAL_FALLBACK_ICON;

  return (
    <div className="dp-result dp-fade-up">
      {/* Summary bar */}
      <div className="dp-summary">
        <div className="dp-summary-item">
          <span className="dp-summary-value">{totalCalories}</span>
          <span className="dp-summary-label">Daily Calories</span>
        </div>
        <div className="dp-summary-item">
          <span className="dp-summary-value">{macros.protein}g</span>
          <span className="dp-summary-label">Protein</span>
        </div>
        <div className="dp-summary-item">
          <span className="dp-summary-value">{macros.carbs}g</span>
          <span className="dp-summary-label">Carbs</span>
        </div>
        <div className="dp-summary-item">
          <span className="dp-summary-value">{macros.fat}g</span>
          <span className="dp-summary-label">Fat</span>
        </div>
      </div>

      {/* Meal cards */}
      <div className="dp-meals">
        {meals.map((meal, i) => (
          <div className="dp-meal" key={i}>
            <div className="dp-meal-head">
              <span className="dp-meal-icon">{icon(meal.type)}</span>
              <h3 className="dp-meal-title">{meal.label}</h3>
              <span className="dp-meal-calories">{mealCalories(meal)} kcal</span>
            </div>
            <ul className="dp-meal-items">
              {(meal.items || []).map((item, j) => (
                <li className="dp-meal-item" key={j}>
                  <div className="dp-meal-item-info">
                    <span className="dp-meal-item-name">{item.name}</span>
                    <span className="dp-meal-item-portion">{item.portion}</span>
                  </div>
                  <div className="dp-meal-item-meta">
                    <span className="dp-meal-item-cal">{item.calories} kcal</span>
                    <span className="dp-meal-item-macros">
                      P {item.macros?.protein ?? 0} · C {item.macros?.carbs ?? 0} · F {item.macros?.fat ?? 0}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="dp-result-actions">
        <button className="btn-secondary" onClick={onEdit}>
          Edit Preferences
        </button>
        <button className="btn-primary" onClick={onRegenerate}>
          Regenerate Plan
        </button>
      </div>
    </div>
  );
}

/* Random rotation of reassuring loader copy. */
function simulateLoadingText() {
  return 'Calculating calorie targets and planning portions for every meal…';
}