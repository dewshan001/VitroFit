// Loads the Google Maps JavaScript API once and searches Places (New) for gyms.
// The key comes from VITE_GOOGLE_MAPS_API_KEY. A browser key is public by nature, so restrict it in
// Google Cloud (HTTP referrers + the Maps JavaScript API and Places API (New) only).

export const MAPS_KEY = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '').trim();
export const hasMapsKey = Boolean(MAPS_KEY && MAPS_KEY !== 'your_google_maps_api_key_here');

export const SEARCH_RADIUS_M = 50000; // Nearby Search (New) allows at most 50 km
export const MAX_RESULTS = 20; // ...and at most 20 places per request

let loading = null;

/** Resolves with `window.google.maps` once the script and the marker library are ready. */
export function loadGoogleMaps() {
  if (!hasMapsKey) return Promise.reject(new Error('Google Maps key is not configured.'));
  if (loading) return loading;

  loading = new Promise((resolve, reject) => {
    // Google calls this when the key is rejected (billing off, referrer blocked, API not enabled).
    window.gm_authFailure = () => {
      loading = null;
      reject(new Error('Google rejected the Maps key (check billing, referrer restrictions and enabled APIs).'));
    };

    window.__vitroGoogleMapsReady = async () => {
      try {
        await window.google.maps.importLibrary('marker');
        resolve(window.google.maps);
      } catch (err) {
        loading = null;
        reject(err);
      }
    };

    const script = document.createElement('script');
    script.async = true;
    script.src =
      `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(MAPS_KEY)}` +
      '&v=weekly&loading=async&callback=__vitroGoogleMapsReady';
    script.onerror = () => {
      loading = null;
      reject(new Error('Could not load Google Maps. Check your connection.'));
    };
    document.head.appendChild(script);
  });
  return loading;
}

export function haversineMeters(a, b) {
  const rad = (d) => (d * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(h));
}

/**
 * A Google place as the Geoapify-shaped feature the list, the cards and the verification button
 * already understand (coordinates are [lng, lat], distance is in metres).
 */
export function toFeature(place, origin) {
  const lat = place?.location?.latitude;
  const lng = place?.location?.longitude;
  if (!place?.id || typeof lat !== 'number' || typeof lng !== 'number') return null;
  return {
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [lng, lat] },
    properties: {
      place_id: place.id,
      name: place.displayName?.text,
      formatted: place.formattedAddress,
      website: place.websiteUri,
      distance: origin ? Math.round(haversineMeters(origin, { lat, lng })) : undefined,
      datasource: { raw: { phone: place.nationalPhoneNumber } },
    },
  };
}

const FIELD_MASK = [
  'places.id',
  'places.displayName',
  'places.formattedAddress',
  'places.location',
  'places.websiteUri',
  'places.nationalPhoneNumber',
].join(',');

/** Gyms near a point, nearest first. Throws with Google's own message when the request is refused. */
export async function searchNearbyGyms({ lat, lng }, signal) {
  const response = await fetch('https://places.googleapis.com/v1/places:searchNearby', {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      'X-Goog-Api-Key': MAPS_KEY,
      'X-Goog-FieldMask': FIELD_MASK,
    },
    body: JSON.stringify({
      includedTypes: ['gym'],
      languageCode: 'en',
      maxResultCount: MAX_RESULTS,
      rankPreference: 'DISTANCE',
      locationRestriction: { circle: { center: { latitude: lat, longitude: lng }, radius: SEARCH_RADIUS_M } },
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.error?.message || `Places search failed (${response.status}).`);
  }
  const origin = { lat, lng };
  return (data.places || []).map((p) => toFeature(p, origin)).filter(Boolean);
}
