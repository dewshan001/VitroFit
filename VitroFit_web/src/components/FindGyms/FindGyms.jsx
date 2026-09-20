import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import GymMap from './GymMap';
import './FindGyms.css';




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
/* ─────────────────────────────────────────
   MAIN COMPONENT
───────────────────────────────────────── */
export default function FindGyms() {
  const [search, setSearch] = useState('');

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

      {/* ── STICKY SEARCH ── */}
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

          <button id="fg-search-btn" className="fg-search-btn" onClick={() => {}}>
            <IconSearch /> Search
          </button>
        </div>
      </div>

      {/* ── INTERACTIVE MAP ── */}
      <GymMap />



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
    </div>
  );
}
