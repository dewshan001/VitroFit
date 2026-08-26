import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './About.css';

// Core values data
const coreValues = [
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    ),
    title: 'Freedom to Train',
    desc: 'Your workout routine belongs to you — not to any single gym. We let you carry it everywhere.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v4l3 3"/>
      </svg>
    ),
    title: 'Consistency',
    desc: 'Maintain your momentum whether you are on a business trip, vacation, or back home.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    ),
    title: 'Smart Planning',
    desc: 'Create intelligent workout plans that adapt to your available equipment and gym facilities.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="8" y1="6" x2="21" y2="6"/>
        <line x1="8" y1="12" x2="21" y2="12"/>
        <line x1="8" y1="18" x2="21" y2="18"/>
        <line x1="3" y1="6" x2="3.01" y2="6"/>
        <line x1="3" y1="12" x2="3.01" y2="12"/>
        <line x1="3" y1="18" x2="3.01" y2="18"/>
      </svg>
    ),
    title: 'Personalization',
    desc: 'Every plan is tailored to your specific fitness goals, no matter where you train.',
  },
];

// Platform features / team
const teamFeatures = [
  {
    name: 'Smart Gym Finder',
    role: 'Locate nearby partner gyms worldwide in seconds',
    img: '/about_trainer_1.png',
  },
  {
    name: 'Workout Plan Builder',
    role: 'Create and save custom workout plans for any location',
    img: '/about_trainer_2.png',
  },
  {
    name: 'Progress Tracker',
    role: 'Monitor your fitness progress across different gyms',
    img: '/about_trainer_3.png',
  },
  {
    name: 'Timetable Manager',
    role: 'Organize your weekly workout schedule effortlessly',
    img: '/about_trainer_4.png',
  },
  {
    name: 'Travel Mode',
    role: 'Get gym recommendations and plans at your travel destination',
    img: '/about_trainer_5.png',
  },
  {
    name: 'Community Hub',
    role: 'Connect with fellow fitness enthusiasts around the globe',
    img: '/about_trainer_6.png',
  },
];

// Stats counter animation
function StatCounter({ end, suffix = '', duration = 2000 }) {
  const ref = useRef(null);
  const { ref: sectionRef, isVisible } = useScrollAnimation();
  const started = useRef(false);

  useEffect(() => {
    if (!isVisible || started.current) return;
    started.current = true;
    let start = 0;
    const step = end / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= end) {
        start = end;
        clearInterval(timer);
      }
      if (ref.current) {
        ref.current.textContent = Math.floor(start) + suffix;
      }
    }, 16);
    return () => clearInterval(timer);
  }, [isVisible, end, suffix, duration]);

  return (
    <span ref={sectionRef} style={{ display: 'inline' }}>
      <span ref={ref}>0{suffix}</span>
    </span>
  );
}

export default function About() {
  const [videoPlaying, setVideoPlaying] = useState(false);
  const videoRef = useRef(null);

  const heroAnim = useScrollAnimation(0.05);
  const introLeft = useScrollAnimation();
  const introRight = useScrollAnimation();
  const valuesHeader = useScrollAnimation();
  const valuesCards = useScrollAnimation();
  const videoSection = useScrollAnimation();
  const teamHeader = useScrollAnimation();
  const teamGrid = useScrollAnimation();

  const handleVideoPlay = () => {
    setVideoPlaying(true);
    if (videoRef.current) {
      videoRef.current.play();
    }
  };

  return (
    <div id="about" className="about-page">
      {/* ─── HERO BANNER ─── */}
      <section className="about-hero" ref={heroAnim.ref}>
        <img
          src="/about_hero_bg.png"
          alt="VitroFit gym"
          className="about-hero-img"
        />
        <div className="about-hero-overlay" />
        <div className="about-hero-diagonal" />
        <div className={`about-hero-content fade-up ${heroAnim.isVisible ? 'visible' : ''}`}>
          <h1 className="about-hero-title">
            ABOUT <span className="accent">VITROFIT</span>
          </h1>
          <nav className="about-breadcrumb" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="breadcrumb-sep">›</span>
            <span>About Us</span>
          </nav>
        </div>
      </section>

      {/* ─── INTRO / EMPOWERING ─── */}
      <section className="about-intro section">
        <div className="about-intro-inner">
          {/* Gallery */}
          <div className={`about-gallery fade-left ${introLeft.isVisible ? 'visible' : ''}`} ref={introLeft.ref}>
            <div className="gallery-col gallery-col-a">
              <img src="/about_gallery_1.png" alt="Athlete training" className="gallery-img" />
            </div>
            <div className="gallery-col gallery-col-b">
              <div className="gallery-accent-block" />
              <img src="/about_gallery_2.png" alt="Cycling workout" className="gallery-img gallery-img-b" />
            </div>
          </div>

          {/* Text */}
          <div
            className={`about-intro-text fade-right ${introRight.isVisible ? 'visible' : ''}`}
            ref={introRight.ref}
          >
            <h2 className="about-intro-title">
              EMPOWERING <span className="accent">YOUR</span>
              <br />FITNESS ANYWHERE
            </h2>
            <div className="accent-line" />
            <p className="about-intro-desc">
              Welcome to VitroFit — the all-in-one fitness management platform built for people who refuse to let travel disrupt their training. Whether you are at your home gym, a hotel gym, or exploring a new city, VitroFit helps you find the right gym, follow your workout plan, and stay on top of your schedule. Your fitness goals don't pause. Neither do we.
            </p>

            {/* Stats inline */}
            <div className="about-stats-row">
              {[
                { num: 10000, suf: '+', label: 'Active Users' },
                { num: 5000, suf: '+', label: 'Partner Gyms' },
                { num: 500, suf: '+', label: 'Workout Plans' },
              ].map((s, i) => (
                <div className="about-stat" key={i}>
                  <div className="about-stat-num">
                    <StatCounter end={s.num} suffix={s.suf} />
                  </div>
                  <div className="about-stat-label">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── CORE VALUES ─── */}
      <section className="about-values section">
        <div className="container">
          <div
            className={`about-values-header fade-up ${valuesHeader.isVisible ? 'visible' : ''}`}
            ref={valuesHeader.ref}
          >
            <h2 className="section-title">
              OUR <span className="accent">CORE VALUES</span>
            </h2>
            <p className="about-values-sub">guide everything we do</p>
          </div>

          <div className={`about-values-grid fade-up delay-2 ${valuesCards.isVisible ? 'visible' : ''}`} ref={valuesCards.ref}>
            {coreValues.map((v, i) => (
              <div
                className={`value-card fade-up delay-${i + 1} ${valuesCards.isVisible ? 'visible' : ''}`}
                key={v.title}
              >
                <div className="value-icon-wrap">
                  {v.icon}
                </div>
                <h3 className="value-title">{v.title}</h3>
                <p className="value-desc">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── VIDEO EXPERIENCE ─── */}
      <section className="about-video-section" ref={videoSection.ref}>
        <div className={`about-video-wrapper fade-up ${videoSection.isVisible ? 'visible' : ''}`}>
          <img
            src="/about_hero_bg.png"
            alt="Experience VitroFit"
            className="about-video-poster"
          />
          <div className="about-video-overlay" />
          {!videoPlaying && (
            <button className="about-video-play" onClick={handleVideoPlay} aria-label="Play video">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </button>
          )}
          <div className="about-video-text">
            <h2 className="about-video-title">
              EXPERIENCE <span className="accent">VITROFIT</span>
            </h2>
            <p className="about-video-sub">Train Anywhere. Achieve Everything.</p>
          </div>
        </div>
      </section>

      {/* ─── MEET THE EXPERTS ─── */}
      <section className="about-team section">
        <div className="container">
          <div
            className={`about-team-header fade-up ${teamHeader.isVisible ? 'visible' : ''}`}
            ref={teamHeader.ref}
          >
            <div className="about-team-header-row">
              <div>
                <h2 className="section-title">
                  PLATFORM <span className="accent">FEATURES</span>
                </h2>
                <p className="about-team-sub">
                  Everything you need to keep your fitness on track — at home, abroad, or anywhere in between.
                </p>
              </div>
              <Link to="/#classes" className="btn-primary">SEE MORE</Link>
            </div>
          </div>

          <div
            className={`about-team-grid fade-up delay-2 ${teamGrid.isVisible ? 'visible' : ''}`}
            ref={teamGrid.ref}
          >
            {teamFeatures.map((t, i) => (
              <div
                className={`trainer-card fade-up delay-${(i % 3) + 1} ${teamGrid.isVisible ? 'visible' : ''}`}
                key={t.name}
              >
                <div className="trainer-img-wrap">
                  <img src={t.img} alt={t.name} className="trainer-img" />
                  <div className="trainer-book-overlay">
                    <Link to="/#classes" className="trainer-book-btn btn-primary">LEARN MORE</Link>
                  </div>
                </div>
                <div className="trainer-info">
                  <h3 className="trainer-name">{t.name}</h3>
                  <p className="trainer-role">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
