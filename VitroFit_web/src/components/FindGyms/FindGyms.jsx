import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './FindGyms.css';

/* ─────────────────────────────────────────
   MOCK DATA  (replace with API later)
───────────────────────────────────────── */
const GYMS = [
  {
    id: 1,
    name: 'Iron Peak Fitness',
    location: 'Colombo 03, Western Province',
    distance: '0.8 km',
    rating: 4.9,
    reviews: 312,
    badge: 'Top Rated',
    img: 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80',
    amenities: ['Free Weights', 'Cardio Zone', 'Sauna', 'Parking', 'Showers', 'Locker Room'],
    type: ['Strength', 'Cardio'],
    hours: '5:00 AM – 11:00 PM',
    capacity: 80,
    workouts: [
      { name: 'Strength Sculpt', icon: '🏋️', duration: '60 min', level: 'beginner', type: 'Strength' },
      { name: 'HIIT Blast', icon: '⚡', duration: '45 min', level: 'intermediate', type: 'Cardio' },
      { name: 'Power Athlete', icon: '💪', duration: '75 min', level: 'advanced', type: 'Strength' },
      { name: 'Cardio Burn', icon: '🔥', duration: '50 min', level: 'intermediate', type: 'Cardio' },
    ],
  },
  {
    id: 2,
    name: 'ZenFlow Wellness Studio',
    location: 'Nugegoda, Western Province',
    distance: '1.4 km',
    rating: 4.7,
    reviews: 189,
    badge: 'Wellness',
    img: 'https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80',
    amenities: ['Yoga Studio', 'Meditation Room', 'Pilates', 'Juice Bar', 'Showers'],
    type: ['Yoga', 'Wellness'],
    hours: '6:00 AM – 9:00 PM',
    capacity: 40,
    workouts: [
      { name: 'Yoga Flow', icon: '🧘', duration: '60 min', level: 'beginner', type: 'Yoga' },
      { name: 'Zen & Recover', icon: '🌿', duration: '45 min', level: 'beginner', type: 'Wellness' },
      { name: 'Mindful Pilates', icon: '🤸', duration: '55 min', level: 'intermediate', type: 'Pilates' },
    ],
  },
  {
    id: 3,
    name: 'Apex Athletic Club',
    location: 'Dehiwala, Western Province',
    distance: '2.1 km',
    rating: 4.8,
    reviews: 456,
    badge: 'Partner',
    img: 'https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=800&q=80',
    amenities: ['Olympic Weights', 'CrossFit Box', 'Swimming Pool', 'Sauna', 'Café', 'Parking'],
    type: ['Strength', 'CrossFit', 'Swimming'],
    hours: '4:30 AM – 11:00 PM',
    capacity: 150,
    workouts: [
      { name: 'Functional Move', icon: '🤾', duration: '60 min', level: 'advanced', type: 'CrossFit' },
      { name: 'Power Athlete', icon: '💪', duration: '75 min', level: 'advanced', type: 'Strength' },
      { name: 'HIIT Blast', icon: '⚡', duration: '45 min', level: 'intermediate', type: 'Cardio' },
      { name: 'Strength Sculpt', icon: '🏋️', duration: '60 min', level: 'beginner', type: 'Strength' },
      { name: 'Outdoor Athlete', icon: '🏃', duration: '50 min', level: 'intermediate', type: 'Cardio' },
    ],
  },
  {
    id: 4,
    name: 'The Motion Lab',
    location: 'Rajagiriya, Western Province',
    distance: '3.0 km',
    rating: 4.6,
    reviews: 220,
    badge: 'New',
    img: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=800&q=80',
    amenities: ['Treadmills', 'Spin Studio', 'Free Weights', 'Showers', 'Lockers'],
    type: ['Cardio', 'Cycling'],
    hours: '6:00 AM – 10:00 PM',
    capacity: 60,
    workouts: [
      { name: 'Cardio Burn', icon: '🔥', duration: '50 min', level: 'intermediate', type: 'Cardio' },
      { name: 'Outdoor Athlete', icon: '🏃', duration: '45 min', level: 'beginner', type: 'Cardio' },
      { name: 'HIIT Blast', icon: '⚡', duration: '30 min', level: 'intermediate', type: 'Cardio' },
    ],
  },
  {
    id: 5,
    name: 'Pinnacle Sports Centre',
    location: 'Mount Lavinia, Western Province',
    distance: '4.5 km',
    rating: 4.5,
    reviews: 134,
    badge: 'Partner',
    img: 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=800&q=80',
    amenities: ['Sports Courts', 'Gym Floor', 'Pool', 'Café', 'Parking', 'Showers'],
    type: ['Strength', 'Sports', 'Swimming'],
    hours: '5:00 AM – 10:00 PM',
    capacity: 200,
    workouts: [
      { name: 'Strength Sculpt', icon: '🏋️', duration: '60 min', level: 'beginner', type: 'Strength' },
      { name: 'Functional Move', icon: '🤾', duration: '50 min', level: 'intermediate', type: 'CrossFit' },
      { name: 'Hotel Gym Ready', icon: '🏨', duration: '30 min', level: 'beginner', type: 'Minimal' },
    ],
  },
  {
    id: 6,
    name: 'HardCore Gym',
    location: 'Borella, Western Province',
    distance: '5.2 km',
    rating: 4.4,
    reviews: 98,
    badge: null,
    img: 'https://images.unsplash.com/photo-1599058945522-28d584b6f4ff?auto=format&fit=crop&w=800&q=80',
    amenities: ['Heavy Lifting', 'Powerlifting Platform', 'Free Weights', 'Lockers'],
    type: ['Strength', 'Powerlifting'],
    hours: '6:00 AM – 10:00 PM',
    capacity: 50,
    workouts: [
      { name: 'Power Athlete', icon: '💪', duration: '90 min', level: 'advanced', type: 'Strength' },
      { name: 'Strength Sculpt', icon: '🏋️', duration: '60 min', level: 'intermediate', type: 'Strength' },
      { name: 'HIIT Blast', icon: '⚡', duration: '40 min', level: 'advanced', type: 'Cardio' },
    ],
  },
];

const FILTERS = ['All', 'Strength', 'Cardio', 'Yoga', 'Wellness', 'CrossFit', 'Swimming'];

/* ─────────────────────────────────────────
   ICONS
───────────────────────────────────────── */
const IconSearch = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);
const IconLocation = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
  </svg>
);
const IconFilter = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" y1="6" x2="20" y2="6"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="11" y1="18" x2="13" y2="18"/>
  </svg>
);
const IconStar = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
  </svg>
);
const IconDumbbell = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 4v16M18 4v16M4 9h4M16 9h4M4 15h4M16 15h4M8 4h8M8 20h8"/>
  </svg>
);
const IconClose = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconArrow = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
  </svg>
);
const IconClock = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
  </svg>
);
const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

/* ─────────────────────────────────────────
   GYM CARD
───────────────────────────────────────── */
function GymCard({ gym, index, onSelect }) {
  return (
    <div
      className={`fg-gym-card fg-fade-up fg-d${(index % 6) + 1}`}
      onClick={() => onSelect(gym)}
    >
      {/* Image */}
      <div className="fg-gym-card-img-wrap">
        <img src={gym.img} alt={gym.name} className="fg-gym-card-img" />
        {gym.badge && <div className="fg-gym-card-badge">{gym.badge}</div>}
        <div className="fg-gym-card-distance">
          <IconLocation />
          {gym.distance}
        </div>
        <div className="fg-gym-card-overlay">
          <button className="fg-gym-card-overlay-btn">
            View Gym <IconArrow />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="fg-gym-card-body">
        <div className="fg-gym-card-name">{gym.name}</div>
        <div className="fg-gym-card-location">
          <IconLocation />
          {gym.location}
        </div>

        {/* Amenity tags */}
        <div className="fg-gym-amenities">
          {gym.amenities.slice(0, 4).map((a) => (
            <span className="fg-amenity-tag" key={a}>{a}</span>
          ))}
          {gym.amenities.length > 4 && (
            <span className="fg-amenity-tag">+{gym.amenities.length - 4} more</span>
          )}
        </div>

        {/* Meta */}
        <div className="fg-gym-card-meta">
          <div className="fg-gym-rating">
            <div className="fg-gym-stars">
              {Array.from({ length: 5 }).map((_, i) => (
                <span key={i} style={{ opacity: i < Math.round(gym.rating) ? 1 : 0.25 }}>
                  <IconStar />
                </span>
              ))}
            </div>
            <span className="fg-gym-rating-val">{gym.rating}</span>
            <span className="fg-gym-reviews">({gym.reviews})</span>
          </div>
          <div className="fg-gym-plans-count">
            <IconDumbbell />
            {gym.workouts.length} plans
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────
   GYM DETAIL PANEL
───────────────────────────────────────── */
function GymDetailPanel({ gym, onClose }) {
  const [closing, setClosing] = useState(false);

  const handleClose = () => {
    setClosing(true);
    setTimeout(onClose, 340);
  };

  // Lock body scroll while panel open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  return (
    <>
      <div className="fg-panel-backdrop" onClick={handleClose} />
      <div className={`fg-detail-panel${closing ? ' closing' : ''}`}>
        {/* Header image */}
        <div className="fg-panel-header">
          <img src={gym.img} alt={gym.name} className="fg-panel-header-img" />
          <div className="fg-panel-header-overlay" />
          <button className="fg-panel-close" onClick={handleClose} aria-label="Close">
            <IconClose />
          </button>
          <div className="fg-panel-header-info">
            {gym.badge && <div className="fg-gym-card-badge" style={{ position: 'relative', top: 'auto', left: 'auto', display: 'inline-block', marginBottom: '0.5rem' }}>{gym.badge}</div>}
            <div className="fg-panel-name">{gym.name}</div>
            <div className="fg-panel-location">
              <IconLocation />
              {gym.location}
            </div>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="fg-panel-body">
          {/* Stats */}
          <div className="fg-panel-stats">
            <div className="fg-panel-stat">
              <div className="fg-panel-stat-val">{gym.rating}</div>
              <div className="fg-panel-stat-label">Rating</div>
            </div>
            <div className="fg-panel-stat">
              <div className="fg-panel-stat-val">{gym.distance}</div>
              <div className="fg-panel-stat-label">Distance</div>
            </div>
            <div className="fg-panel-stat">
              <div className="fg-panel-stat-val">{gym.workouts.length}</div>
              <div className="fg-panel-stat-label">Plans</div>
            </div>
          </div>

          {/* Hours & Capacity */}
          <div>
            <div className="fg-panel-section-label">Gym Info</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <IconClock />
                <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '1px', marginRight: '0.25rem' }}>Hours:</span>
                {gym.hours}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <IconCheck />
                <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '1px', marginRight: '0.25rem' }}>Capacity:</span>
                {gym.capacity} members
              </div>
            </div>
          </div>

          {/* Amenities */}
          <div>
            <div className="fg-panel-section-label">Amenities</div>
            <div className="fg-panel-amenities">
              {gym.amenities.map((a) => (
                <div className="fg-panel-amenity" key={a}>
                  <IconCheck />
                  {a}
                </div>
              ))}
            </div>
          </div>

          {/* Available Workouts */}
          <div>
            <div className="fg-panel-section-label">Available Workout Plans</div>
            <div className="fg-panel-workouts">
              {gym.workouts.map((w) => (
                <div className="fg-workout-item" key={w.name}>
                  <div className="fg-workout-icon">{w.icon}</div>
                  <div className="fg-workout-info">
                    <div className="fg-workout-name">{w.name}</div>
                    <div className="fg-workout-meta">
                      <span className="fg-workout-tag">
                        <IconClock /> {w.duration}
                      </span>
                      <span className="fg-workout-tag">{w.type}</span>
                    </div>
                  </div>
                  <span className={`fg-workout-level ${w.level}`}>
                    {w.level.charAt(0).toUpperCase() + w.level.slice(1)}
                  </span>
                  <span className="fg-workout-arrow"><IconArrow /></span>
                </div>
              ))}
            </div>
          </div>

          {/* CTA */}
          <div className="fg-panel-cta">
            <button className="btn-primary">Add to My Gyms</button>
            <button className="btn-secondary">Get Directions</button>
          </div>
        </div>
      </div>
    </>
  );
}

/* ─────────────────────────────────────────
   MAIN COMPONENT
───────────────────────────────────────── */
export default function FindGyms() {
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');
  const [sortBy, setSortBy] = useState('distance');
  const [selectedGym, setSelectedGym] = useState(null);

  // Scroll-based reveal
  useEffect(() => {
    window.scrollTo(0, 0);
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add('visible'); }),
      { threshold: 0.08 }
    );
    document.querySelectorAll('.fg-fade-up, .fg-fade-left').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Re-run observer when filter changes (new cards rendered)
  useEffect(() => {
    const timer = setTimeout(() => {
      const observer = new IntersectionObserver(
        (entries) => entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add('visible'); }),
        { threshold: 0.08 }
      );
      document.querySelectorAll('.fg-fade-up:not(.visible)').forEach((el) => observer.observe(el));
      return () => observer.disconnect();
    }, 50);
    return () => clearTimeout(timer);
  }, [activeFilter, search]);

  // Filtered & sorted gyms
  const filtered = GYMS
    .filter((g) => {
      const matchSearch =
        g.name.toLowerCase().includes(search.toLowerCase()) ||
        g.location.toLowerCase().includes(search.toLowerCase());
      const matchFilter = activeFilter === 'All' || g.type.includes(activeFilter);
      return matchSearch && matchFilter;
    })
    .sort((a, b) => {
      if (sortBy === 'rating') return b.rating - a.rating;
      if (sortBy === 'reviews') return b.reviews - a.reviews;
      return parseFloat(a.distance) - parseFloat(b.distance);
    });

  return (
    <div className="find-gyms-page">
      {/* ── HERO ── */}
      <section className="fg-hero">
        <img
          src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=2000&q=80"
          alt="Find Gyms Hero"
          className="fg-hero-img"
        />
        <div className="fg-hero-overlay" />
        <div className="fg-hero-accent-shape" />
        <div className="container fg-hero-content">
          <div className="fg-breadcrumb fg-fade-up">
            Home &gt; <span>Find Gyms</span>
          </div>
          <div className="fg-hero-eyebrow fg-fade-up fg-d1">
            <div className="fg-hero-eyebrow-line" />
            <span className="fg-hero-eyebrow-text">VitroFit Partner Network</span>
          </div>
          <h1 className="fg-hero-title fg-fade-up fg-d2">
            <span className="outline-text">FIND</span> YOUR<br />
            PERFECT GYM
          </h1>
          <p className="fg-hero-sub fg-fade-up fg-d3">
            Discover thousands of partner gyms near you — at home, on the road, or anywhere in the world.
            Filter by workout type, distance, and amenities.
          </p>
        </div>
      </section>

      {/* ── STICKY SEARCH & FILTER ── */}
      <div className="fg-search-section">
        <div className="fg-search-bar">
          {/* Location search */}
          <div className="fg-search-group">
            <span className="fg-search-icon"><IconLocation /></span>
            <input
              id="fg-location-input"
              type="text"
              placeholder="Search by city, area or gym name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Workout type */}
          <div className="fg-search-group" style={{ flex: '0 1 220px' }}>
            <span className="fg-search-icon"><IconDumbbell /></span>
            <select
              id="fg-workout-select"
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
            >
              {FILTERS.map((f) => <option key={f} value={f}>{f === 'All' ? 'All Workout Types' : f}</option>)}
            </select>
          </div>

          {/* Sort */}
          <div className="fg-search-group" style={{ flex: '0 1 180px' }}>
            <span className="fg-search-icon"><IconFilter /></span>
            <select id="fg-sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="distance">Nearest First</option>
              <option value="rating">Top Rated</option>
              <option value="reviews">Most Reviewed</option>
            </select>
          </div>

          <button id="fg-search-btn" className="fg-search-btn" onClick={() => {}}>
            <IconSearch /> Search
          </button>
        </div>

        {/* Quick filter tags */}
        <div className="fg-filters-row">
          <span className="fg-filter-label">Filter:</span>
          {FILTERS.map((f) => (
            <button
              key={f}
              className={`fg-filter-tag${activeFilter === f ? ' active' : ''}`}
              onClick={() => setActiveFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* ── MAP PLACEHOLDER ── */}
      <div className="fg-map-banner">
        <div className="fg-map-grid" />
        <div className="fg-map-dots">
          <div className="fg-map-dot-ring">
            <div className="fg-map-dot-inner" />
          </div>
          <span className="fg-map-text">Interactive Map — Coming Soon</span>
        </div>
      </div>

      {/* ── RESULTS COUNT ── */}
      <div className="fg-results-header">
        <div className="fg-results-count">
          Showing <strong>{filtered.length}</strong> gyms
          {activeFilter !== 'All' && <> in <strong>{activeFilter}</strong></>}
          {search && <> matching <strong>"{search}"</strong></>}
        </div>
        <select
          className="fg-sort-select"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="distance">Sort: Nearest</option>
          <option value="rating">Sort: Top Rated</option>
          <option value="reviews">Sort: Most Reviewed</option>
        </select>
      </div>

      {/* ── GYMS GRID ── */}
      <div className="fg-grid-section">
        {filtered.length > 0 ? (
          <div className="fg-gyms-grid">
            {filtered.map((gym, i) => (
              <GymCard key={gym.id} gym={gym} index={i} onSelect={setSelectedGym} />
            ))}
          </div>
        ) : (
          <div className="fg-empty">
            <div className="fg-empty-icon">🔍</div>
            <h3>No gyms found</h3>
            <p>Try adjusting your search or filter criteria.</p>
          </div>
        )}
      </div>

      {/* ── CTA BANNER ── */}
      <section className="fg-cta-section">
        <img
          src="https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=2000&q=80"
          alt="CTA Background"
          className="fg-cta-img"
        />
        <div className="fg-cta-overlay" />
        <div className="fg-cta-accent-shape" />
        <div className="fg-cta-content">
          <div>
            <h2 className="fg-cta-title fg-fade-up">
              OWN A GYM?<br />
              <span className="accent">JOIN THE NETWORK</span>
            </h2>
            <p className="fg-cta-sub fg-fade-up fg-d1">
              List your gym on VitroFit and reach thousands of active fitness users looking for a great place to train.
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'flex-start' }} className="fg-fade-up fg-d2">
            <button className="btn-primary">Register Your Gym</button>
            <Link to="/about" className="btn-secondary">Learn More</Link>
          </div>
        </div>
      </section>

      {/* ── GYM DETAIL PANEL ── */}
      {selectedGym && (
        <GymDetailPanel
          gym={selectedGym}
          onClose={() => setSelectedGym(null)}
        />
      )}
    </div>
  );
}
