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
 * Starts generating a diet plan from the given preferences. Returns
 * immediately with a workflowId + status "running" — it does NOT wait for
 * the AI to finish. Call pollDietWorkflow() with the returned workflowId to
 * watch live progress and get the finished plan (or a clear failure reason).
 */
export async function generateDietPlan(prefs) {
  const response = await fetch(`${DIET_AGENT_API_URL}/generate`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(prefs),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data?.detail || 'Could not start generating a diet plan. Please try again.');
  }

  return data;
}

/** One-shot fetch of a workflow's current state (status, live steps, and — once terminal — the plan or the reason it failed). */
export async function getDietWorkflow(workflowId) {
  const response = await fetch(`${DIET_AGENT_API_URL}/workflows/${workflowId}`, {
    method: 'GET',
    headers: authHeaders(),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data?.detail || 'Could not check plan generation status.');
  }

  return data;
}

const TERMINAL_WORKFLOW_STATUSES = new Set(['completed', 'failed', 'rejected']);

/**
 * Polls a workflow started by generateDietPlan() until it reaches a terminal
 * status, calling onProgress with each poll's raw workflow detail so the
 * caller can show live per-agent progress (completedSteps) while waiting.
 * Resolves with the finished plan on success; throws (with completedSteps
 * attached) on failure/rejection or if it never finishes within timeoutMs.
 */
export async function pollDietWorkflow(workflowId, { onProgress, intervalMs = 2000, timeoutMs = 240000 } = {}) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const detail = await getDietWorkflow(workflowId);
    onProgress?.(detail);

    if (TERMINAL_WORKFLOW_STATUSES.has(detail.status)) {
      if (detail.status === 'completed') {
        return {
          totalCalories: detail.targets?.totalCalories ?? 0,
          macros: detail.targets?.macros ?? { protein: 0, carbs: 0, fat: 0 },
          meals: detail.meals ?? [],
          withinTolerance: detail.finalOutcome?.withinTolerance ?? true,
          workflowId: detail.id,
          status: detail.status,
          riskLevel: detail.riskLevel,
          plan: detail.plan,
          completedSteps: detail.completedSteps,
          requiresApproval: detail.approvalStatus === 'pending',
          // Set (only) when a requested edit couldn't be applied — the plan
          // above is still the last good one, this just explains why a
          // refine() call didn't change it.
          note: detail.message || null,
        };
      }
      const error = new Error(detail.message || 'Could not generate a diet plan. Please try again.');
      error.completedSteps = detail.completedSteps || [];
      throw error;
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error('Generating your plan is taking longer than expected. Please try again.');
}

/**
 * Requests a targeted, free-text edit to an already-generated plan (e.g.
 * "instead of rice at lunch, include something else") instead of starting
 * over from the preferences form. Returns immediately with status "running";
 * poll with pollDietWorkflow(workflowId) exactly as after generateDietPlan()
 * to watch progress and get the updated plan.
 */
export async function refineDietPlan(workflowId, instruction) {
  const response = await fetch(`${DIET_AGENT_API_URL}/workflows/${workflowId}/refine`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ instruction }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data?.detail || 'Could not apply that change. Please try again.');
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
