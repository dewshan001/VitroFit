const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

export async function fitnessRequest(path, method = 'GET', body) {
  const auth = JSON.parse(sessionStorage.getItem('vitrofitAuth') || 'null');
  const response = await fetch(`${base}/fitness/${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${auth?.accessToken || ''}` },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    signal: AbortSignal.timeout(150000),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const validation = data.errors && Object.values(data.errors).flat().join(' ');
    throw new Error(data.message || validation || (response.status === 401 ? 'Please sign in again.' : 'Fitness request failed.'));
  }
  return data;
}
