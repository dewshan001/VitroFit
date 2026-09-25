const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

function getToken() {
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    return stored ? JSON.parse(stored).accessToken : '';
  } catch {
    return '';
  }
}

export async function getWorkouts() {
  const token = getToken();

  const response = await fetch(`${API_BASE_URL}/workouts`, {
    headers: {
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
