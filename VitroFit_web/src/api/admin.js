const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

/** Authenticated GET */
async function apiAuthGet(path) {
  let token = '';
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    token = stored ? JSON.parse(stored).accessToken : '';
  } catch { /* ignore */ }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.error || data?.message || 'Server error. Please try again.';
    throw new Error(error);
  }

  return data;
}

/** Authenticated POST */
async function apiAuthPost(path, body) {
  let token = '';
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    token = stored ? JSON.parse(stored).accessToken : '';
  } catch { /* ignore */ }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.error || data?.message || 'Server error. Please try again.';
    throw new Error(error);
  }

  return data;
}

/** Authenticated DELETE */
async function apiAuthDelete(path) {
  let token = '';
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    token = stored ? JSON.parse(stored).accessToken : '';
  } catch { /* ignore */ }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.error || data?.message || 'Server error. Please try again.';
    throw new Error(error);
  }

  return data;
}

// -------------------------------------------------------------
// Admin Endpoints
// -------------------------------------------------------------

export function getUsersByRole(role) {
  const query = role !== null && role !== undefined ? `?role=${role}` : '';
  return apiAuthGet(`/admin/users${query}`);
}

export function createUser(userData) {
  return apiAuthPost('/admin/users', userData);
}

export function deleteUser(userId) {
  return apiAuthDelete(`/admin/users/${userId}`);
}
