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
    title: 'Community',
    desc: 'Fostering a sense of belonging and support.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8v4l3 3"/>
      </svg>
    ),
    title: 'Inclusivity',
    desc: 'Embracing diversity in fitness for all body types and abilities.',
  },
  {
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    ),
    title: 'Innovation',
    desc: 'Offering cutting-edge workouts and technology.',
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
    desc: 'Tailoring fitness plans to individual needs.',
  },
];

// Trainers data
const trainers = [
  {
    name: 'Alexandra Rodriguez',
    role: 'Strength & Conditioning Specialist',
    img: '/about_trainer_1.png',
  },
  {
    name: 'David Chen',
    role: 'Certified Yoga Instructor',
    img: '/about_trainer_2.png',
  },
  {
    name: 'Emily Turner',
    role: 'Nutrition and Wellness Coach',
    img: '/about_trainer_3.png',
  },
  {
    name: 'Mark Johnson',
    role: 'High-Intensity Interval Training (HIIT) Expert',
    img: '/about_trainer_4.png',
  },
  {
    name: 'Dr. Maya Patel',
    role: 'Injury Prevention Specialist',
    img: '/about_trainer_5.png',
  },
  {
    name: 'Sophie Nguyen',
    role: 'Pilates and Flexibility Trainer',
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
              <br />FITNESS JOURNEY
            </h2>
            <div className="accent-line" />
            <p className="about-intro-desc">
              Welcome to VitroFit, where we believe that a healthier, happier you begins
              with personalized fitness and a supportive community. Our state-of-the-art
              studio is not just a gym; it's a space for transformation, where individuals
              of all fitness levels come together to achieve their goals. With a commitment
              to innovation and inclusivity, VitroFit is more than a workout — it's a lifestyle.
            </p>

            {/* Stats inline */}
            <div className="about-stats-row">
              {[
                { num: 500, suf: '+', label: 'Members' },
                { num: 30, suf: '+', label: 'Classes' },
                { num: 10, suf: '', label: 'Trainers' },
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
            <p className="about-video-sub">Where Your Fitness Journey Thrives</p>
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
                  MEET <span className="accent">THE EXPERT</span>
                </h2>
                <p className="about-team-sub">
                  Each member of our team brings unique expertise to ensure a well-rounded and holistic fitness experience.
                </p>
              </div>
              <Link to="/#classes" className="btn-primary">SEE MORE</Link>
            </div>
          </div>

          <div
            className={`about-team-grid fade-up delay-2 ${teamGrid.isVisible ? 'visible' : ''}`}
            ref={teamGrid.ref}
          >
            {trainers.map((t, i) => (
              <div
                className={`trainer-card fade-up delay-${(i % 3) + 1} ${teamGrid.isVisible ? 'visible' : ''}`}
                key={t.name}
              >
                <div className="trainer-img-wrap">
                  <img src={t.img} alt={t.name} className="trainer-img" />
                  <div className="trainer-book-overlay">
                    <Link to="/#classes" className="trainer-book-btn btn-primary">BOOK NOW</Link>
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
