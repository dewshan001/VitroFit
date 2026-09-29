const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';
const BASE = '/gym-agent/workflows';

function readToken() {
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    return stored ? JSON.parse(stored).accessToken : '';
  } catch {
    return '';
  }
}

/** ProblemDetails (ASP.NET) or {error}/{message} -> one readable string. */
function errorMessage(data) {
  if (data?.errors && typeof data.errors === 'object') {
    const first = Object.values(data.errors).flat()[0];
    if (first) return first;
  }
  return data?.detail || data?.error || data?.message || data?.title || 'Server error. Please try again.';
}

async function request(method, path, body) {
  const token = readToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(errorMessage(data));
    error.status = response.status;
    throw error;
  }
  return data;
}

// -------------------------------------------------------------
// Gym multi-agent workflow (ASP.NET Core -> internal agent service)
// -------------------------------------------------------------

/** Runs waiting for a decision. Admin / Gym_Owner only. */
export const getPendingWorkflows = () => request('GET', `${BASE}/pending`);

/** Every run (approvers) - the API scopes this to the caller's own runs for other roles. */
export const getAllWorkflows = () => request('GET', `${BASE}?all=true`);

/** Full detail: plan, facts, workouts, validation results, steps, tool calls, approval fields. */
export const getWorkflow = (id) => request('GET', `${BASE}/${encodeURIComponent(id)}`);

/** Chronological execution summary (each step preceded by its tool calls). */
export const getWorkflowEvents = (id) => request('GET', `${BASE}/${encodeURIComponent(id)}/events`);

export const startWorkflow = (gym) => request('POST', BASE, gym);

export const approveWorkflow = (id, reason) =>
  request('POST', `${BASE}/${encodeURIComponent(id)}/approve`, { reason });

export const rejectWorkflow = (id, reason) =>
  request('POST', `${BASE}/${encodeURIComponent(id)}/reject`, { reason });

/** Send back to the agents with feedback. A reason is mandatory. */
export const reviseWorkflow = (id, reason) =>
  request('POST', `${BASE}/${encodeURIComponent(id)}/revise`, { reason });
