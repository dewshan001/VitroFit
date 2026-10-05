const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

/** Limits shared with the server-side validator (GymApplicationValidator). */
export const GYM_LIMITS = {
  maxImageBytes: 5 * 1024 * 1024,
  maxLicenseBytes: 5 * 1024 * 1024,
  minPhotos: 1,
  maxPhotos: 5,
  maxEquipment: 30,
  maxClasses: 20,
  maxTagLength: 60,
  imageTypes: ['image/jpeg', 'image/png', 'image/webp'],
  licenseTypes: ['application/pdf', 'image/jpeg', 'image/png'],
};

/**
 * Register a gym owner: account + gym details + photos (+ licence) in one multipart request.
 * The same call re-applies for a rejected owner (same email and password).
 * Throws an Error whose `errors` lists every problem the server found.
 */
export async function registerGymOwner(formData) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/register-gym-owner`, { method: 'POST', body: formData });
  } catch {
    throw new Error('Could not reach the server. Check your connection and try again.');
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = response.status === 429
      ? 'Too many applications from this connection. Please try again later.'
      : response.status === 413
        ? 'The files are too large. Each photo and the licence must be 5 MB or smaller.'
        : data?.error || data?.title || data?.message || 'Server error. Please try again.';
    const error = new Error(message);
    error.errors = Array.isArray(data?.errors) ? data.errors : [];
    throw error;
  }

  return data;
}
