// Helpers for the "Submit for verification" button on Find Gyms cards.
// Kept free of React so the request-building rules are easy to reason about and test.

const ADMIN_ROLES = [2, 'Admin'];
const GYM_OWNER_ROLES = [3, 'Gym_Owner'];

// Limits mirror StartGymWorkflowRequest in the ASP.NET API. A value over the limit is dropped
// (not truncated): a cut-off phone number or address would look verified but be wrong.
const MAX_ID = 255;
const MAX_TEXT = 500;
const MAX_PHONE = 50;
const MAX_EMAIL = 255;
const MAX_HOURS = 255;

const EMAIL_RE = /^[^\s@;,]+@[^\s@;,]+\.[^\s@;,]+$/;

/** Same roles the API allows to approve: Admin and Gym_Owner (role arrives as a number or a string). */
export function canSubmitForVerification(user) {
  const role = user?.role;
  return ADMIN_ROLES.includes(role) || GYM_OWNER_ROLES.includes(role);
}

function clean(value, max) {
  if (typeof value !== 'string') return undefined;
  const trimmed = value.trim();
  return trimmed && trimmed.length <= max ? trimmed : undefined;
}

/** OSM stores several numbers/emails in one tag separated by ; or , : keep the first. */
function firstOf(value) {
  return typeof value === 'string' ? value.split(/[;,]/)[0] : undefined;
}

/** Same id the list and map use for a place, so a card and its workflow always agree. */
export function placeIdOf(place) {
  const [lng, lat] = place?.geometry?.coordinates || [];
  return place?.properties?.place_id || `${lat}-${lng}`;
}

/**
 * Maps a Geoapify place to a StartGymWorkflowRequest body, or null when the place cannot be
 * submitted (no usable id or name).
 */
export function buildVerificationRequest(place) {
  const props = place?.properties || {};
  const raw = props.datasource?.raw || {};
  const [lng, lat] = place?.geometry?.coordinates || [];

  // Without a provider id we can only identify a place by its coordinates; with neither, the
  // fallback id would be "undefined-undefined" and collide across gyms, so refuse instead.
  const hasCoords = Number.isFinite(lat) && Number.isFinite(lng);
  if (!props.place_id && !hasCoords) return null;

  const placeId = clean(placeIdOf(place), MAX_ID);
  const name = clean(props.name || props.address_line1 || 'Gym & Fitness Center', MAX_ID);
  if (!placeId || !name) return null;

  const email = clean(firstOf(raw.email || raw['contact:email']), MAX_EMAIL);

  const body = {
    placeId,
    name,
    address: clean(props.formatted || props.address_line2, MAX_TEXT),
    website: clean(props.website || raw.website, MAX_TEXT),
    knownPhone: clean(firstOf(raw.phone || raw['contact:phone']), MAX_PHONE),
    knownEmail: email && EMAIL_RE.test(email) ? email : undefined,
    knownHours: clean(raw.opening_hours, MAX_HOURS),
    lat: Number.isFinite(lat) && lat >= -90 && lat <= 90 ? lat : undefined,
    lng: Number.isFinite(lng) && lng >= -180 && lng <= 180 ? lng : undefined,
  };

  return Object.fromEntries(Object.entries(body).filter(([, v]) => v !== undefined));
}
