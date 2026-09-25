const DIET_AGENT_API_URL = import.meta.env.VITE_DIET_AGENT_API_URL || 'http://localhost:8002/api/diet';

function authHeaders() {
  let token = '';
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    token = stored ? JSON.parse(stored).accessToken : '';
  } catch { /* ignore */ }
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

/**
 * Generates a diet plan from the given preferences via DietPlanService.
 * Not saved server-side yet — call confirmDietPlan() once the user accepts it.
 */
export async function generateDietPlan(prefs) {
  const response = await fetch(`${DIET_AGENT_API_URL}/generate`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(prefs),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.detail || 'Could not generate a diet plan. Please try again.';
    throw new Error(error);
  }

  return data;
}

/**
 * Fetches the logged-in user's previously confirmed/saved diet plans.
 */
export async function fetchSavedDietPlans() {
  const response = await fetch(`${DIET_AGENT_API_URL}/plans`, {
    method: 'GET',
    headers: authHeaders(),
  });

  const data = await response.json().catch(() => ([]));

  if (!response.ok) {
    const error = data?.detail || 'Could not load your saved plans.';
    throw new Error(error);
  }

  return data;
}

/**
 * Persists a (possibly user-edited) generated plan, along with the inputs
 * that produced it, once the user explicitly confirms it.
 */
export async function confirmDietPlan(inputs, plan) {
  const response = await fetch(`${DIET_AGENT_API_URL}/confirm`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      inputs,
      totalCalories: plan.totalCalories,
      macros: plan.macros,
      meals: plan.meals,
      withinTolerance: plan.withinTolerance ?? true,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.detail || 'Could not save this plan. Please try again.';
    throw new Error(error);
  }

  return data;
}

/**
 * Overwrites a previously saved plan (and the inputs that produced it) with a
 * newly regenerated version, keeping the same saved-plan id.
 */
export async function updateDietPlan(planId, inputs, plan) {
  const response = await fetch(`${DIET_AGENT_API_URL}/plans/${planId}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({
      inputs,
      totalCalories: plan.totalCalories,
      macros: plan.macros,
      meals: plan.meals,
      withinTolerance: plan.withinTolerance ?? true,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.detail || 'Could not update this plan. Please try again.';
    throw new Error(error);
  }

  return data;
}

/**
 * Deletes a previously saved plan.
 */
export async function deleteDietPlan(planId) {
  const response = await fetch(`${DIET_AGENT_API_URL}/plans/${planId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = data?.detail || 'Could not delete this plan. Please try again.';
    throw new Error(error);
  }
}
