const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

async function apiPost(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
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

/** Authenticated POST — attaches the Bearer token from localStorage */
async function apiAuthPost(path, body) {
  let token = '';
  try {
    const stored = localStorage.getItem('vitrofitAuth');
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

async function apiAuthUpload(path, formData) {
  let token = '';
  try {
    const stored = localStorage.getItem('vitrofitAuth');
    token = stored ? JSON.parse(stored).accessToken : '';
  } catch { /* ignore */ }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.error || data?.message || 'Server error. Please try again.';
    throw new Error(error);
  }

  return data;
}

export function login({ email, password }) {
  return apiPost('/auth/login', { email, password });
}

export function register({ firstName, lastName, email, phone, password }) {
  return apiPost('/auth/register', { firstName, lastName, email, phone, password });
}

export function uploadProfileImage(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiAuthUpload('/auth/me/photo', formData);
}

/**
 * Change the current user's password.
 * Requires a valid access token in localStorage.
 */
export function changePassword({ currentPassword, newPassword }) {
  return apiAuthPost('/auth/change-password', {
    currentPassword,
    newPassword,
  });
}

/** Authenticated DELETE — attaches the Bearer token from localStorage */
async function apiAuthDelete(path) {
  let token = '';
  try {
    const stored = localStorage.getItem('vitrofitAuth');
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

export function deleteAccount() {
  return apiAuthDelete('/auth/me');
}
