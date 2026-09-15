import { useEffect, useState, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchGymDetails } from '../../api/gyms';
import './GymMap.css';

/* ─────────────────────────────────────────
   FIX LEAFLET DEFAULT ICON PATHS
───────────────────────────────────────── */
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
});

/* ─────────────────────────────────────────
   CUSTOM USER-LOCATION MARKER
───────────────────────────────────────── */
const userIcon = L.divIcon({
  className: 'gym-map-user-icon',
  html: `
    <div class="gym-map-user-pulse">
      <div class="gym-map-user-dot"></div>
    </div>
  `,
  iconSize: [40, 40],
  iconAnchor: [20, 20],
  popupAnchor: [0, -22],
});

/* ─────────────────────────────────────────
   CUSTOM GYM / PLACE MARKER
───────────────────────────────────────── */
const gymIcon = L.divIcon({
  className: 'gym-map-place-icon',
  html: `
    <div class="gym-marker-pin">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 4v16M18 4v16M4 9h4M16 9h4M4 15h4M16 15h4M8 4h8M8 20h8"/>
      </svg>
    </div>
  `,
  iconSize: [34, 34],
  iconAnchor: [17, 34],
  popupAnchor: [0, -34],
});

/* ─────────────────────────────────────────
   MAP CONTROLLER (Resize + Center watcher)
───────────────────────────────────────── */
function MapController({ coords, onCenterChange }) {
  const map = useMap();
  const hasCentered = useRef(false);
  const debounceTimer = useRef(null);

  const reportCenter = useCallback(() => {
    if (!onCenterChange) return;
    const center = map.getCenter();
    onCenterChange({ lat: center.lat, lng: center.lng });
  }, [map, onCenterChange]);

  useEffect(() => {
    map.invalidateSize();
    const t1 = setTimeout(() => {
      map.invalidateSize();
      reportCenter();
    }, 250);

    const handleResize = () => map.invalidateSize();
    window.addEventListener('resize', handleResize);

    const handleMoveEnd = () => {
      clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => {
        reportCenter();
      }, 300);
    };

    map.on('moveend', handleMoveEnd);

    return () => {
      clearTimeout(t1);
      clearTimeout(debounceTimer.current);
      window.removeEventListener('resize', handleResize);
      map.off('moveend', handleMoveEnd);
    };
  }, [map, reportCenter]);

  useEffect(() => {
    if (coords && !hasCentered.current) {
      hasCentered.current = true;
      map.flyTo([coords.lat, coords.lng], 11, { duration: 1.6 });
    }
  }, [coords, map]);

  return null;
}

/* ─────────────────────────────────────────
   GYM EQUIPMENT / CLASSES (fetched on demand
   when a marker's popup is opened)
───────────────────────────────────────── */
const SOURCE_LABELS = {
  verified: 'Verified by gym',
  'ai-scraped': "AI summary of the gym's website",
  'ai-generic': 'AI best guess (no site data)',
};

function GymDetailsSection({ status }) {
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

  const loadGymDetails = useCallback((placeId, place) => {
    setGymDetails((prev) => {
      if (prev[placeId] && (prev[placeId].loading || prev[placeId].data)) return prev;
      return { ...prev, [placeId]: { loading: true } };
    });

    fetchGymDetails(place)
      .then((data) => setGymDetails((prev) => ({ ...prev, [placeId]: { loading: false, data } })))
      .catch(() => setGymDetails((prev) => ({ ...prev, [placeId]: { loading: false, error: true } })));
  }, []);

  const apiKey = (import.meta.env.VITE_GEOAPIFY_API_KEY || '').trim();
  const isKeyValid = Boolean(apiKey && apiKey !== 'your_geoapify_api_key_here');

  const DEFAULT_CENTER = [6.9271, 79.8612];
  const DEFAULT_ZOOM = 11;

  const tileUrl = isKeyValid
    ? `https://maps.geoapify.com/v1/tile/dark-matter/{z}/{x}/{y}.png?apiKey=${apiKey}`
    : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

  const tileAttribution = isKeyValid
    ? 'Powered by <a href="https://www.geoapify.com/" target="_blank">Geoapify</a> | &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
    : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

  const fetchPlaces = useCallback(async (params) => {
    if (!isKeyValid) return;
    setLoadingPlaces(true);

    try {
      const lat = params?.lat || DEFAULT_CENTER[0];
      const lng = params?.lng || DEFAULT_CENTER[1];
      const categories = 'sport.fitness';
      const url = `https://api.geoapify.com/v2/places?categories=${categories}&filter=circle:${lng},${lat},50000&bias=proximity:${lng},${lat}&limit=80&apiKey=${apiKey}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error('Places API error');

      const data = await res.json();
      if (data && data.features) {
        setPlaces(data.features);
      }
    } catch (err) {
      console.error('Failed to fetch places:', err);
    } finally {
      setLoadingPlaces(false);
    }
  }, [apiKey, isKeyValid]);

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError(true);
      setLocating(false);
      fetchPlaces({ lat: DEFAULT_CENTER[0], lng: DEFAULT_CENTER[1] });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setUserCoords(coords);
        setLocating(false);
        fetchPlaces({ lat: coords.lat, lng: coords.lng });
      },
      () => {
        setLocationError(true);
        setLocating(false);
        fetchPlaces({ lat: DEFAULT_CENTER[0], lng: DEFAULT_CENTER[1] });
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  }, [fetchPlaces]);

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
            <MapContainer
              center={DEFAULT_CENTER}
              zoom={DEFAULT_ZOOM}
              minZoom={3}
              maxZoom={19}
              scrollWheelZoom={true}
              style={{ height: '100%', width: '100%' }}
              zoomControl={false}
              attributionControl={true}
            >
              <TileLayer
                url={tileUrl}
                attribution={tileAttribution}
                maxZoom={20}
                crossOrigin="anonymous"
              />

              <MapController coords={userCoords} onCenterChange={fetchPlaces} />
              <ZoomControl position="bottomleft" />

              {/* User location marker */}
              {userCoords && (
                <Marker position={[userCoords.lat, userCoords.lng]} icon={userIcon} zIndexOffset={1000}>
                  <Popup className="gym-map-popup">
                    <div className="gym-map-popup-content">
                      <span className="gym-map-popup-icon">&#128205;</span>
                      <span className="gym-map-popup-label">You are here</span>
                    </div>
                  </Popup>
                </Marker>
              )}

              {/* Gym markers */}
              {places.map((place, idx) => {
                const props = place.properties || {};
                const coords = place.geometry?.coordinates;
                if (!coords || coords.length < 2) return null;
                const [lng, lat] = coords;

                const placeName = props.name || props.address_line1 || 'Gym & Fitness Center';
                const placeAddress = props.formatted || props.address_line2 || '';
                const distance = props.distance ? (props.distance / 1000).toFixed(1) : null;
                const placeId = props.place_id || `${lat}-${lng}-${idx}`;
                const website = props.website || props.datasource?.raw?.website;

                return (
                  <Marker
                    key={placeId}
                    position={[lat, lng]}
                    icon={gymIcon}
                    eventHandlers={{
                      popupopen: () => loadGymDetails(placeId, {
                        placeId, name: placeName, lat, lng, address: placeAddress, website,
                      }),
                    }}
                  >
                    <Popup className="gym-map-place-popup">
                      <div className="gym-place-popup-card">
                        <div className="gym-place-popup-header">
                          <div className="gym-place-popup-badge">Gym / Fitness</div>
                          {distance && <span className="gym-place-popup-dist">{distance} km away</span>}
                        </div>
                        <div className="gym-place-popup-title">{placeName}</div>
                        {placeAddress && (
                          <div className="gym-place-popup-address">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                            </svg>
                            {placeAddress}
                          </div>
                        )}
                        <GymDetailsSection status={gymDetails[placeId]} />
                        <div className="gym-place-popup-actions">
                          <a
                            href={`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="gym-place-popup-btn"
                          >
                            Directions &rarr;
                          </a>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>

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
                  <strong>50 km</strong> radius
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
    </div>
  );
}
