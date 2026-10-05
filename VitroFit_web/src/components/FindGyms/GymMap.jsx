import { useEffect, useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { fetchGymDetails, isSignedIn, SignInRequiredError } from '../../api/gyms';
import { loadGoogleMaps, searchNearbyGyms, SEARCH_RADIUS_M } from '../../api/googleMaps';
import GymList from './GymList';
import WorkoutSuggestionsModal from './WorkoutSuggestionsModal';
import { SOURCE_LABELS, isVerifiedSource } from './gymSourceLabels';
import VerifiedBadge from './VerifiedBadge';
import './GymMap.css';

const DEFAULT_CENTER = { lat: 6.9271, lng: 79.8612 };
const DEFAULT_ZOOM = 11;
const USER_ZOOM = 12;

/* Marker elements reuse the existing pin styles. */
function userMarkerElement() {
  const el = document.createElement('div');
  el.className = 'gym-map-user-icon';
  el.innerHTML = '<div class="gym-map-user-pulse"><div class="gym-map-user-dot"></div></div>';
  return el;
}

function gymMarkerElement() {
  const el = document.createElement('div');
  el.className = 'gym-map-place-icon';
  el.innerHTML = `
    <div class="gym-marker-pin">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 4v16M18 4v16M4 9h4M16 9h4M4 15h4M16 15h4M8 4h8M8 20h8"/>
      </svg>
    </div>`;
  return el;
}

/** The fields the map, list and verification code read from a place feature. */
function placeFields(place, idx = 0) {
  const props = place.properties || {};
  const [lng, lat] = place.geometry?.coordinates || [];
  return {
    lat,
    lng,
    placeId: props.place_id || `${lat}-${lng}-${idx}`,
    name: props.name || props.address_line1 || 'Gym & Fitness Center',
    address: props.formatted || props.address_line2 || '',
    distance: props.distance ? (props.distance / 1000).toFixed(1) : null,
    website: props.website || props.datasource?.raw?.website,
  };
}

/* ─────────────────────────────────────────
   GYM EQUIPMENT / CLASSES (fetched on demand
   when a marker's popup is opened)
───────────────────────────────────────── */
function GymDetailsSection({ status }) {
  if (status?.authRequired) {
    return (
      <div className="gym-place-popup-details gym-place-popup-details--empty">
        <Link to="/login">Sign in</Link> to see equipment and classes.
      </div>
    );
  }
  if (!status || status.loading) {
    return <div className="gym-place-popup-details gym-place-popup-details--loading">Loading equipment & classes…</div>;
  }
  if (status.error) {
    return <div className="gym-place-popup-details gym-place-popup-details--error">Couldn&apos;t load gym details.</div>;
  }

  const { equipment = [], classes = [], source } = status.data || {};
  if (equipment.length === 0 && classes.length === 0) {
    return <div className="gym-place-popup-details gym-place-popup-details--empty">No equipment/class info available yet.</div>;
  }

  return (
    <div className="gym-place-popup-details">
      {equipment.length > 0 && (
        <div className="gym-place-popup-details-group">
          <span className="gym-place-popup-details-label">Equipment</span>
          <div className="gym-place-popup-tags">
            {equipment.map((item) => <span className="gym-place-popup-tag" key={item}>{item}</span>)}
          </div>
        </div>
      )}
      {classes.length > 0 && (
        <div className="gym-place-popup-details-group">
          <span className="gym-place-popup-details-label">Classes</span>
          <div className="gym-place-popup-tags">
            {classes.map((item) => <span className="gym-place-popup-tag" key={item}>{item}</span>)}
          </div>
        </div>
      )}
      {source && <div className="gym-place-popup-details-source">{SOURCE_LABELS[source] || source}</div>}
    </div>
  );
}

export default function GymMap() {
  const [userCoords, setUserCoords] = useState(null);
  const [places, setPlaces] = useState([]);
  const [loadingPlaces, setLoadingPlaces] = useState(false);
  const [locationError, setLocationError] = useState(false);
  const [locating, setLocating] = useState(true);
  const [gymDetails, setGymDetails] = useState({});
  const [workoutModalTarget, setWorkoutModalTarget] = useState(null);
  const workoutCacheRef = useRef(new Map());

  const requestIdRef = useRef(0);

  const loadGymDetails = useCallback((placeId, place) => {
    // Equipment/classes come from the AI service behind the API, which needs a login. Logged-out
    // visitors still get the map and the list, and are asked to sign in instead of seeing an error.
    if (!isSignedIn()) {
      setGymDetails((prev) => ({ ...prev, [placeId]: { loading: false, authRequired: true } }));
      return;
    }

    setGymDetails((prev) => {
      if (prev[placeId] && (prev[placeId].loading || prev[placeId].data)) return prev;
      return { ...prev, [placeId]: { loading: true } };
    });

    fetchGymDetails(place)
      .then((data) => setGymDetails((prev) => ({ ...prev, [placeId]: { loading: false, data } })))
      .catch((err) => setGymDetails((prev) => ({
        ...prev,
        [placeId]: err instanceof SignInRequiredError
          ? { loading: false, authRequired: true }
          : { loading: false, error: true },
      })));
  }, []);

  const [mapsState, setMapsState] = useState({ status: 'loading' });
  const [placesError, setPlacesError] = useState('');
  const [selectedId, setSelectedId] = useState(null);

  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const infoWindowRef = useRef(null);
  const infoContentRef = useRef(null);
  const userMarkerRef = useRef(null);
  const markersRef = useRef(new Map());
  const abortRef = useRef(null);
  const hasCenteredRef = useRef(false);

  if (!infoContentRef.current && typeof document !== 'undefined') {
    infoContentRef.current = document.createElement('div');
  }

  const fetchPlaces = useCallback(async (center) => {
    const requestId = ++requestIdRef.current;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoadingPlaces(true);
    setPlacesError('');

    try {
      const found = await searchNearbyGyms(center, controller.signal);
      if (requestId !== requestIdRef.current) return;
      setPlaces(found);
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Failed to fetch places:', err);
      if (requestId === requestIdRef.current) setPlacesError(err.message || 'Could not search for gyms.');
    } finally {
      if (requestId === requestIdRef.current) setLoadingPlaces(false);
    }
  }, []);

  // Load the Google Maps script once.
  useEffect(() => {
    let cancelled = false;
    loadGoogleMaps()
      .then(() => { if (!cancelled) setMapsState({ status: 'ready' }); })
      .catch((err) => {
        console.error('Google Maps failed to load:', err);
        if (!cancelled) setMapsState({ status: 'error', message: err.message });
      });
    return () => { cancelled = true; };
  }, []);

  // Create the map; every pan or zoom (after it settles) searches the area under the map centre.
  useEffect(() => {
    if (mapsState.status !== 'ready' || !containerRef.current || mapRef.current) return undefined;
    const { maps } = window.google;
    const map = new maps.Map(containerRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      minZoom: 3,
      mapId: 'DEMO_MAP_ID',
      colorScheme: maps.ColorScheme.DARK,
      disableDefaultUI: true,
      zoomControl: true,
      gestureHandling: 'greedy',
      clickableIcons: false,
    });
    mapRef.current = map;

    const infoWindow = new maps.InfoWindow({ maxWidth: 360 });
    infoWindow.addListener('closeclick', () => setSelectedId(null));
    infoWindowRef.current = infoWindow;

    let timer;
    const listener = map.addListener('idle', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const c = map.getCenter();
        fetchPlaces({ lat: c.lat(), lng: c.lng() });
      }, 300);
    });

    return () => {
      clearTimeout(timer);
      listener.remove();
      abortRef.current?.abort();
    };
  }, [mapsState.status, fetchPlaces]);

  // Browser location: centre the map there (the map's idle event then searches that area).
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError(true);
      setLocating(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setLocating(false);
      },
      () => {
        setLocationError(true);
        setLocating(false);
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  }, []);

  // "You are here" marker, and fly there once.
  useEffect(() => {
    const map = mapRef.current;
    if (mapsState.status !== 'ready' || !map || !userCoords) return;
    const { AdvancedMarkerElement } = window.google.maps.marker;
    if (userMarkerRef.current) userMarkerRef.current.map = null;
    userMarkerRef.current = new AdvancedMarkerElement({
      map, position: userCoords, content: userMarkerElement(), title: 'You are here', zIndex: 1000,
    });
    if (!hasCenteredRef.current) {
      hasCenteredRef.current = true;
      map.panTo(userCoords);
      map.setZoom(USER_ZOOM);
    }
  }, [mapsState.status, userCoords]);

  // One marker per gym; clicking opens the card.
  useEffect(() => {
    const map = mapRef.current;
    if (mapsState.status !== 'ready' || !map) return;
    const { AdvancedMarkerElement } = window.google.maps.marker;
    markersRef.current.forEach((m) => { m.map = null; });
    markersRef.current = new Map();
    places.forEach((place, idx) => {
      const f = placeFields(place, idx);
      if (typeof f.lat !== 'number' || typeof f.lng !== 'number') return;
      const marker = new AdvancedMarkerElement({
        map, position: { lat: f.lat, lng: f.lng }, content: gymMarkerElement(), title: f.name, gmpClickable: true,
      });
      marker.addEventListener('gmp-click', () => setSelectedId(f.placeId));
      markersRef.current.set(f.placeId, marker);
    });
  }, [mapsState.status, places]);

  const selectedPlace = places
    .map((p, i) => ({ p, f: placeFields(p, i) }))
    .find(({ f }) => f.placeId === selectedId);

  // Open the info window on the selected marker and fetch that gym's details.
  useEffect(() => {
    const infoWindow = infoWindowRef.current;
    if (!infoWindow) return;
    const marker = selectedId ? markersRef.current.get(selectedId) : null;
    if (!marker || !selectedPlace) {
      infoWindow.close();
      return;
    }
    const { f } = selectedPlace;
    infoWindow.setContent(infoContentRef.current);
    infoWindow.open({ map: mapRef.current, anchor: marker });
    loadGymDetails(f.placeId, {
      placeId: f.placeId, name: f.name, lat: f.lat, lng: f.lng, address: f.address, website: f.website,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, places]);

  return (
    <div className="gym-map-section">
      <div className="gym-map-inner">

        {/* ── HEADER ── */}
        <div className="gym-map-header">
          <div className="gym-map-header-left">
            <div className="gym-map-eyebrow">
              <div className="gym-map-eyebrow-line" />
              <span className="gym-map-eyebrow-text">Explore The Area</span>
            </div>
            <h2 className="gym-map-title">
              <span className="outline-text">MAP</span> VIEW
            </h2>
          </div>

          <div className="gym-map-location-status">
            {locating && (
              <div className="gym-map-status gym-map-status--locating">
                <span className="gym-map-status-dot gym-map-status-dot--pulse" />
                Detecting your location&hellip;
              </div>
            )}
            {!locating && !locationError && userCoords && (
              <div className="gym-map-status gym-map-status--found">
                <span className="gym-map-status-dot gym-map-status-dot--active" />
                Location active {places.length > 0 && `• ${places.length} places found`}
              </div>
            )}
            {!locating && locationError && (
              <div className="gym-map-status gym-map-status--error">
                <span className="gym-map-status-dot gym-map-status-dot--error" />
                Default area {places.length > 0 && `• ${places.length} places found`}
              </div>
            )}
            {loadingPlaces && (
              <div className="gym-map-status gym-map-status--loading">
                <span className="gym-map-status-dot gym-map-status-dot--pulse" />
                Searching places&hellip;
              </div>
            )}
          </div>
        </div>

        {/* ── MAP FRAME ── */}
        <div className="gym-map-frame">
          {/* Corner accent brackets */}
          <div className="gym-map-corner gym-map-corner--tl" />
          <div className="gym-map-corner gym-map-corner--tr" />
          <div className="gym-map-corner gym-map-corner--bl" />
          <div className="gym-map-corner gym-map-corner--br" />

          {/* Map */}
          <div className="gym-map-container">
            <div ref={containerRef} className="gym-map-canvas" />

            {mapsState.status === 'loading' && (
              <div className="gym-map-overlay-msg">Loading map&hellip;</div>
            )}
            {mapsState.status === 'error' && (
              <div className="gym-map-overlay-msg gym-map-overlay-msg--error">
                <strong>The map couldn&apos;t be loaded.</strong>
                <span>{mapsState.message}</span>
              </div>
            )}
            {placesError && mapsState.status === 'ready' && (
              <div className="gym-map-overlay-msg gym-map-overlay-msg--toast">
                Couldn&apos;t search for gyms: {placesError}
              </div>
            )}

            {/* Gym card shown inside Google's info window */}
            {selectedPlace && infoContentRef.current && createPortal(
              (() => {
                const { f } = selectedPlace;
                const status = gymDetails[f.placeId];
                return (
                  <div className="gym-place-popup-card">
                    <div className="gym-place-popup-header">
                      <div className="gym-place-popup-badge">Gym / Fitness</div>
                      {isVerifiedSource(status?.data?.source) && <VerifiedBadge />}
                      {f.distance && <span className="gym-place-popup-dist">{f.distance} km away</span>}
                    </div>
                    <div className="gym-place-popup-title">{f.name}</div>
                    {f.address && (
                      <div className="gym-place-popup-address">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                        </svg>
                        {f.address}
                      </div>
                    )}
                    <GymDetailsSection status={status} />
                    <div className="gym-place-popup-actions">
                      <a
                        href={`https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lng}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="gym-place-popup-btn"
                      >
                        Directions &rarr;
                      </a>
                      <button
                        type="button"
                        className="gym-place-popup-btn gym-place-popup-btn--workouts"
                        onClick={() => setWorkoutModalTarget({
                          placeId: f.placeId,
                          name: f.name,
                          equipment: status?.data?.equipment || [],
                          classes: status?.data?.classes || [],
                        })}
                      >
                        Find Possible Workouts
                      </button>
                    </div>
                  </div>
                );
              })(),
              infoContentRef.current
            )}

            {/* Stats overlay at bottom of map */}
            <div className="gym-map-stats-bar">
              <div className="gym-map-stats-bar-left">
                {places.length > 0 && (
                  <>
                    <div className="gym-map-stat-chip">
                      <strong>{places.length}</strong> gyms found
                    </div>
                    <div className="gym-map-stat-divider" />
                  </>
                )}
                <div className="gym-map-stat-chip">
                  <strong>{SEARCH_RADIUS_M / 1000} km</strong> radius
                </div>
                {userCoords && (
                  <>
                    <div className="gym-map-stat-divider" />
                    <div className="gym-map-stat-chip">
                      📍 Live location
                    </div>
                  </>
                )}
              </div>
              <div className="gym-map-scroll-hint">Scroll to zoom · Drag to pan</div>
            </div>
          </div>
        </div>

        {/* ── LEGEND ── */}
        <div className="gym-map-legend">
          <div className="gym-map-legend-item">
            <div className="gym-map-legend-dot gym-map-legend-dot--user" />
            Your location
          </div>
          <div className="gym-map-legend-divider" />
          <div className="gym-map-legend-item">
            <div className="gym-map-legend-pin" />
            Gym / Fitness centre
          </div>
          <div className="gym-map-legend-divider" />
          <div className="gym-map-legend-item">
            Click a pin to see details
          </div>
        </div>

      </div>

      <GymList
        places={places}
        userCoords={userCoords}
        loadingPlaces={loadingPlaces}
        gymDetails={gymDetails}
        onLoadDetails={loadGymDetails}
      />

      <WorkoutSuggestionsModal
        isOpen={!!workoutModalTarget}
        onClose={() => setWorkoutModalTarget(null)}
        gymName={workoutModalTarget?.name}
        place={workoutModalTarget}
        cachedResult={workoutModalTarget ? workoutCacheRef.current.get(workoutModalTarget.placeId) : null}
        onResult={(placeId, data) => workoutCacheRef.current.set(placeId, data)}
      />
    </div>
  );
}
