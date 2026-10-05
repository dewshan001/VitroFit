const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

function getToken() {
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    return stored ? JSON.parse(stored).accessToken : '';
  } catch {
    return '';
  }
}

export async function apiAuthRequest(path, method, body) {
  const token = getToken();

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
    const error = data?.error || data?.message || 'Server error. Please try again.';
    throw new Error(error);
  }

  return data;
}

export function getTimetable() {
  return apiAuthRequest('/timetable', 'GET');
}

export function createSlot({ day, startTime, endTime, title, workoutId }) {
  return apiAuthRequest('/timetable', 'POST', { day, startTime, endTime, title, workoutId });
}

export function updateSlot(id, { day, startTime, endTime, title, workoutId }) {
  return apiAuthRequest(`/timetable/${id}`, 'PUT', { day, startTime, endTime, title, workoutId });
}

export function deleteSlot(id) {
  return apiAuthRequest(`/timetable/${id}`, 'DELETE');
}

export function getWorkflows() {
  return apiAuthRequest('/fitness/workflows?page=1', 'GET');
}

export function generateSmartTimetable(workflowId, preferences) {
  const qs = preferences ? `?preferences=${encodeURIComponent(preferences)}` : '';
  return apiAuthRequest(`/fitness/workflows/${workflowId}/timetable${qs}`, 'POST');
}

/** The latest timetable request: { proposal: null | { id, status: 'Pending'|'Approved'|'Rejected', slots, longTermImpact, reviewNote, reviewerName, reviewedAt, createdAt } } */
export function getTimetableProposal() {
  return apiAuthRequest('/timetable/proposal', 'GET');
}

export function cancelTimetableProposal(id) {
  return apiAuthRequest(`/timetable/proposal/${id}/cancel`, 'POST');
}
