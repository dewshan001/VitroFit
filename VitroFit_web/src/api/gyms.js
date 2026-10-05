// Gym details and workout suggestions. These go through the ASP.NET Core API only, with the signed-in
// user's JWT; the AI service behind it is internal and is never called from the browser.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

// Limits mirror the API's validation; over-limit values are dropped rather than cut off.
const MAX_ID = 255;
const MAX_TEXT = 500;
const MAX_PHONE = 50;
const MAX_SHORT = 255;
const MAX_ITEMS = 60;
const MAX_ITEM_LENGTH = 80;

/** Thrown when there is no login (or it has expired): the UI shows "sign in" instead of an error. */
export class SignInRequiredError extends Error {
  constructor(message = 'Sign in to see equipment, classes and workout ideas.') {
    super(message);
    this.name = 'SignInRequiredError';
  }
}

function accessToken() {
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    return stored ? JSON.parse(stored).accessToken || '' : '';
  } catch {
    return '';
  }
}

export function isSignedIn() {
  return Boolean(accessToken());
}

function text(value, max) {
  if (typeof value !== 'string') return undefined;
  const trimmed = value.trim();
  return trimmed && trimmed.length <= max ? trimmed : undefined;
}

function list(values) {
  return (Array.isArray(values) ? values : [])
    .filter((v) => typeof v === 'string' && v.length > 0 && v.length <= MAX_ITEM_LENGTH)
    .slice(0, MAX_ITEMS);
}

function withoutUndefined(object) {
  return Object.fromEntries(Object.entries(object).filter(([, v]) => v !== undefined));
}

/** Body for POST /api/gyms/details (camelCase, validated by the API). */
export function buildDetailsBody(place) {
  return withoutUndefined({
    placeId: text(place.placeId, MAX_ID),
    name: text(place.name, MAX_ID),
    lat: Number.isFinite(place.lat) && Math.abs(place.lat) <= 90 ? place.lat : undefined,
    lng: Number.isFinite(place.lng) && Math.abs(place.lng) <= 180 ? place.lng : undefined,
    address: text(place.address, MAX_TEXT),
    website: text(place.website, MAX_TEXT),
    phone: text(place.phone, MAX_PHONE),
    email: text(place.email, MAX_SHORT),
    openingHours: text(place.openingHours, MAX_SHORT),
  });
}

/** Body for POST /api/gyms/workouts. */
export function buildWorkoutsBody(place) {
  return {
    placeId: text(place.placeId, MAX_ID),
    name: text(place.name, MAX_ID),
    equipment: list(place.equipment),
    classes: list(place.classes),
  };
}

async function post(path, body, fallbackMessage) {
  const token = accessToken();
  if (!token) throw new SignInRequiredError();

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('Could not reach the server. Check your connection and try again.');
  }

  const data = await response.json().catch(() => ({}));
  if (response.ok) return data;

  const error = (() => {
    switch (response.status) {
      case 401:
        return new SignInRequiredError('Your session has expired. Please sign in again.');
      case 403:
        return new Error('You do not have permission to do this.');
      case 429:
        return new Error('Too many requests. Please wait a moment and try again.');
      case 503:
        return new Error('The gym service is unavailable right now. Please try again later.');
      case 504:
        return new Error('The gym service took too long to answer. Please try again.');
      default:
        return new Error(data?.detail || data?.title || fallbackMessage);
    }
  })();
  error.status = response.status;
  throw error;
}

/**
 * Equipment/classes for a gym place (AI-enriched and cached server-side, or verified by an admin).
 * `place` carries the fields of a Geoapify nearby-search result.
 */
export function fetchGymDetails(place) {
  return post('/gyms/details', buildDetailsBody(place), 'Could not load gym details.');
}

/**
 * AI-suggested workouts for a gym, based on its known equipment/classes.
 * `place` should be `{ placeId, name, equipment, classes }`.
 */
export function fetchGymWorkouts(place) {
  return post('/gyms/workouts', buildWorkoutsBody(place), 'Could not load workout suggestions.');
}
