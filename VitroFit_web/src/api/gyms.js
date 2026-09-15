const GYM_AGENT_API_URL = import.meta.env.VITE_GYM_AGENT_API_URL || 'http://localhost:8001/api';

/**
 * Fetches equipment/classes for a gym place, enriching via the GymAgentService
 * (scrapes the gym's website + LLM extraction, cached server-side) on cache miss.
 * `place` should carry the fields returned by the Geoapify nearby-search result.
 */
export async function fetchGymDetails(place) {
  const response = await fetch(`${GYM_AGENT_API_URL}/gyms/details`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      place_id: place.placeId,
      name: place.name,
      lat: place.lat,
      lng: place.lng,
      address: place.address,
      website: place.website,
    }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = data?.detail || 'Could not load gym details.';
    throw new Error(error);
  }

  return data;
}
