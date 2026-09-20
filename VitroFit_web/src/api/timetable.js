const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

function getToken() {
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    return stored ? JSON.parse(stored).accessToken : '';
  } catch {
    return '';
  }
}

async function apiAuthRequest(path, method, body) {
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

export function createSlot({ day, startTime, endTime, title }) {
  return apiAuthRequest('/timetable', 'POST', { day, startTime, endTime, title });
}

export function updateSlot(id, { day, startTime, endTime, title }) {
  return apiAuthRequest(`/timetable/${id}`, 'PUT', { day, startTime, endTime, title });
}

export function deleteSlot(id) {
  return apiAuthRequest(`/timetable/${id}`, 'DELETE');
}
