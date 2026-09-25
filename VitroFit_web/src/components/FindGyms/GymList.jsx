import { useEffect, useMemo, useRef, useState } from 'react';
import { SOURCE_LABELS } from './gymSourceLabels';
import './GymList.css';

// Space out detail requests so we never hammer the LLM enrichment
// backend with a burst of simultaneous calls (causes rate-limit failures).
const DETAIL_FETCH_STAGGER_MS = 600;

const PAGE_SIZE = 5;

const IconLocation = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
  </svg>
);
const IconDumbbell = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 4v16M18 4v16M4 9h4M16 9h4M4 15h4M16 15h4M8 4h8M8 20h8"/>
  </svg>
);
const IconArrow = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
  </svg>
);
const IconChevronDown = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);
const IconPhone = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
  </svg>
);
const IconGlobe = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
  </svg>
);
const IconMail = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="22,6 12,13 2,6"/>
  </svg>
);
const IconClock = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
  </svg>
);

function GymDetailsBody({ status }) {
  if (!status || status.loading) {
    return (
      <div className="gl-details gl-details--loading">
        <div className="gl-progress">
          <div className="gl-progress-bar" />
        </div>
        <span className="gl-progress-label">Loading gym details&hellip;</span>
      </div>
    );
  }

  if (status.error) {
    return <div className="gl-details gl-details--error">Couldn&apos;t load gym details.</div>;
  }

  const { equipment = [], classes = [], source } = status.data || {};
  if (equipment.length === 0 && classes.length === 0) {
    return <div className="gl-details gl-details--empty">No equipment/class info available yet.</div>;
  }

  return (
    <div className="gl-details">
      {equipment.length > 0 && (
        <div className="gl-details-group">
          <span className="gl-details-label">Equipment</span>
          <div className="gl-tags">
            {equipment.map((item) => <span className="gl-tag" key={item}>{item}</span>)}
          </div>
        </div>
      )}
      {classes.length > 0 && (
        <div className="gl-details-group">
          <span className="gl-details-label">Classes</span>
          <div className="gl-tags">
            {classes.map((item) => <span className="gl-tag" key={item}>{item}</span>)}
          </div>
        </div>
      )}
      {source && <div className="gl-details-source">{SOURCE_LABELS[source] || source}</div>}
    </div>
  );
}

function GymContactBlock({ raw, website, agentData }) {
  const phone = agentData?.phone || raw.phone || raw['contact:phone'];
  const email = agentData?.email || raw.email || raw['contact:email'];
  const hours = agentData?.opening_hours || raw.opening_hours;

  if (!phone && !email && !website && !hours) return null;

  const phoneHref = phone ? phone.split(/[;,]/)[0].trim() : null;

  return (
    <div className="gl-contact">
      {phone && (
        <a className="gl-contact-row gl-contact-link" href={`tel:${phoneHref}`}>
          <IconPhone /> {phone}
        </a>
      )}
      {hours && (
        <div className="gl-contact-row">
          <IconClock /> {hours}
        </div>
      )}
      {website && (
        <a
          className="gl-contact-row gl-contact-link"
          href={website.startsWith('http') ? website : `https://${website}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <IconGlobe /> Visit website
        </a>
      )}
      {email && (
        <a className="gl-contact-row gl-contact-link" href={`mailto:${email}`}>
          <IconMail /> {email}
        </a>
      )}
    </div>
  );
}

function GymCard({ place, index, status }) {
  const props = place.properties || {};
  const coords = place.geometry?.coordinates;
  const [lng, lat] = coords || [];
  const raw = props.datasource?.raw || {};

  const name = props.name || props.address_line1 || 'Gym & Fitness Center';
  const address = props.formatted || props.address_line2 || '';
  const distance = props.distance != null ? (props.distance / 1000).toFixed(1) : null;
  const website = props.website || raw.website;

  return (
    <div className={`gl-card gl-fade-up gl-d${(index % 5) + 1}`}>
      <div className="gl-card-header">
        <div className="gl-card-badge"><IconDumbbell /> Gym / Fitness</div>
        {distance && <div className="gl-card-distance"><IconLocation />{distance} km away</div>}
      </div>

      <div className="gl-card-name">{name}</div>
      {address && (
        <div className="gl-card-address">
          <IconLocation />
          {address}
        </div>
      )}

      <GymContactBlock raw={raw} website={website} agentData={status?.data} />

      <GymDetailsBody status={status} />

      {lat != null && lng != null && (
        <a
          href={`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`}
          target="_blank"
          rel="noopener noreferrer"
          className="gl-card-directions"
        >
          Directions <IconArrow />
        </a>
      )}
    </div>
  );
}

function GymCardSkeleton({ index }) {
  return (
    <div className={`gl-card gl-card--skeleton gl-fade-up gl-d${(index % 5) + 1}`}>
      <div className="gl-skeleton-line gl-skeleton-line--badge" />
      <div className="gl-skeleton-line gl-skeleton-line--title" />
      <div className="gl-skeleton-line gl-skeleton-line--sub" />
      <div className="gl-progress"><div className="gl-progress-bar" /></div>
    </div>
  );
}

export default function GymList({ places, userCoords, loadingPlaces, gymDetails, onLoadDetails }) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const sorted = useMemo(() => {
    return [...places].sort((a, b) => {
      const da = a.properties?.distance ?? Infinity;
      const db = b.properties?.distance ?? Infinity;
      return da - db;
    });
  }, [places]);

  const visible = sorted.slice(0, visibleCount);

  const scheduledRef = useRef(new Set());
  const staggerIndexRef = useRef(0);

  useEffect(() => {
    const timers = [];

    visible.forEach((place) => {
      const props = place.properties || {};
      const coords = place.geometry?.coordinates;
      if (!coords || coords.length < 2) return;
      const [lng, lat] = coords;
      const placeId = props.place_id || `${lat}-${lng}`;

      if (scheduledRef.current.has(placeId)) return;
      const existing = gymDetails[placeId];
      if (existing && (existing.loading || existing.data)) return;

      scheduledRef.current.add(placeId);
      const delay = staggerIndexRef.current * DETAIL_FETCH_STAGGER_MS;
      staggerIndexRef.current += 1;

      const timer = setTimeout(() => {
        const raw = props.datasource?.raw || {};
        onLoadDetails(placeId, {
          placeId,
          name: props.name || props.address_line1 || 'Gym & Fitness Center',
          lat,
          lng,
          address: props.formatted || props.address_line2 || '',
          website: props.website || raw.website,
          phone: raw.phone || raw['contact:phone'],
          email: raw.email || raw['contact:email'],
          openingHours: raw.opening_hours,
        });
      }, delay);
      timers.push(timer);
    });

    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible.map((p) => p.properties?.place_id).join(',')]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [userCoords?.lat, userCoords?.lng]);

  return (
    <div className="gym-list-section">
      <div className="gl-header">
        <div className="gl-eyebrow">
          <div className="gl-eyebrow-line" />
          <span className="gl-eyebrow-text">Nearest To You</span>
        </div>
        <h3 className="gl-title">
          <span className="outline-text">GYM</span> LIST
        </h3>
      </div>

      {places.length === 0 && loadingPlaces && (
        <div className="gl-grid">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => <GymCardSkeleton key={i} index={i} />)}
        </div>
      )}

      {places.length === 0 && !loadingPlaces && (
        <div className="gl-empty">No gyms found nearby.</div>
      )}

      {places.length > 0 && (
        <>
          <div className="gl-grid">
            {visible.map((place, idx) => {
              const props = place.properties || {};
              const coords = place.geometry?.coordinates;
              const [lng, lat] = coords || [];
              const placeId = props.place_id || `${lat}-${lng}-${idx}`;
              return (
                <GymCard
                  key={placeId}
                  place={place}
                  index={idx}
                  status={gymDetails[placeId]}
                />
              );
            })}
          </div>

          {visibleCount < sorted.length && (
            <div className="gl-load-more-wrap">
              <button
                className="gl-load-more-btn"
                onClick={() => setVisibleCount((c) => Math.min(c + PAGE_SIZE, sorted.length))}
              >
                Load More <IconChevronDown />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
