import { useEffect } from 'react';
import './ClassDetail.css';

const FireIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" fill="var(--bg-primary)"/>
  </svg>
);

const MuscleIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12.5 11c-1.381 0-2.5-1.119-2.5-2.5S11.119 6 12.5 6 15 7.119 15 8.5 13.881 11 12.5 11z" fill="var(--bg-primary)"/>
    <path d="M2 13h5.5l1.5-1.5V9" />
    <path d="M7 16h6" />
    <path d="M13 22v-3.5" />
    <path d="M22 17.5c0-1.5-1-2.5-2.5-2.5h-4l-3-3" />
    <path d="M16 11V6" />
  </svg>
); // Approximate for arm

const HeartIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
  </svg>
);

const DropIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
    <path d="M12 11L9.5 15h5L12 19" fill="#c8f000" stroke="#c8f000"/>
  </svg>
);

const ClockIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14" stroke="#c8f000"/>
  </svg>
);

const BrainIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 4c-3-2-6 0-6 4 0 2-2 3-2 5 0 2 1 3 3 4 0 2 2 4 5 4s5-2 5-4c2-1 3-2 3-4 0-2-2-3-2-5 0-4-3-6-6-4z"/>
    <path d="M12 4v16" stroke="#c8f000"/>
  </svg>
);

const LayoutIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
    <line x1="3" y1="9" x2="21" y2="9" stroke="#c8f000"/>
    <line x1="9" y1="21" x2="9" y2="9" stroke="#c8f000"/>
  </svg>
);

const UsersIcon = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)" stroke="var(--bg-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);


const benefits = [
  { icon: <FireIcon />, title: "Calorie Torch", desc: "Burn a maximum number of calories in a short amount of time." },
  { icon: <MuscleIcon />, title: "Full-Body Conditioning", desc: "Target multiple muscle groups for a comprehensive workout." },
  { icon: <HeartIcon />, title: "Increased Endurance", desc: "Increased Endurance: Boost cardiovascular stamina." },
  { icon: <DropIcon />, title: "Metabolic Boost", desc: "Experience the afterburn effect for continued calorie burn post-workout." },
  { icon: <ClockIcon />, title: "Time Efficiency", desc: "Achieve results with a time-efficient, intense workout." },
  { icon: <BrainIcon />, title: "Mental Focus", desc: "Enhance mental resilience and focus through challenging intervals." },
  { icon: <LayoutIcon />, title: "Adaptability", desc: "Suitable for various fitness levels with adaptable exercises." },
  { icon: <UsersIcon />, title: "Community Engagement", desc: "Join a supportive community for motivation and camaraderie." },
];

const relatedClasses = [
  {
    img: "https://images.unsplash.com/photo-1594381898411-846e7d193883?auto=format&fit=crop&w=800&q=80",
    title: "CARDIO KICK",
    type: "Kickboxing Cardio",
    level: "INTERMEDIATE"
  },
  {
    img: "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80",
    title: "MINDFUL PILATES",
    type: "Pilates",
    level: "INTERMEDIATE"
  },
  {
    img: "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80",
    title: "CYCLE FUSION",
    type: "Indoor Cycling",
    level: "INTERMEDIATE"
  }
];

export default function ClassDetail() {
  useEffect(() => {
    window.scrollTo(0, 0);

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.1 }
    );

    document.querySelectorAll('.fade-up, .fade-left, .fade-right').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="class-detail">
      {/* Hero Banner */}
      <section className="cd-hero">
        <img 
          src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=2000&q=80" 
          alt="Class Hero Background" 
          className="cd-hero-img" 
        />
        <div className="cd-hero-overlay"></div>
        <div className="cd-hero-accent-shape"></div>
        <div className="container cd-hero-content">
          <div className="cd-breadcrumb fade-up">
            Home &gt; <span>Classes</span>
          </div>
          <h1 className="cd-hero-title fade-up delay-1">
            <span className="outline-text">VITRO</span>FIT
          </h1>
        </div>
      </section>

      {/* Info Section */}
      <section className="cd-info-section container section">
        <div className="cd-info-grid">
          <div className="cd-info-image-container fade-right">
            <img 
              src="https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=1000&q=80" 
              alt="Woman on treadmill" 
              className="cd-info-image"
            />
            <div className="cd-info-image-accent"></div>
          </div>
          <div className="cd-info-text fade-left">
            <div className="cd-info-item">
              <h4>Type</h4>
              <p>High-Intensity Interval Training (HIIT)</p>
            </div>
            <div className="cd-info-item">
              <h4>Level</h4>
              <p>Intermediate</p>
            </div>
            <div className="cd-info-item">
              <h4>Duration</h4>
              <p>60 minutes</p>
            </div>
            <div className="cd-info-item">
              <h4>Description</h4>
              <p>Immerse yourself in a dynamic 60-minute session that seamlessly blends cardiovascular exercises with strength training intervals. FitFusion is designed to push your limits, ignite your metabolism, and leave you feeling invigorated.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="cd-benefits-section container section">
        <h2 className="cd-section-title text-center fade-up">BENEFITS</h2>
        <div className="cd-benefits-grid">
          {benefits.map((benefit, idx) => (
            <div key={idx} className={`cd-benefit-card fade-up delay-${(idx % 4) + 1}`}>
              <div className="cd-benefit-icon">
                {benefit.icon}
              </div>
              <h3 className="cd-benefit-title">{benefit.title}</h3>
              <p className="cd-benefit-desc">{benefit.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Gallery Section */}
      <section className="cd-gallery-section bg-secondary">
        <div className="cd-gallery-grid container section">
          <div className="cd-gallery-col">
             <img src="https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80" alt="Suspension Training" className="cd-gallery-img img-tall fade-up" />
             <img src="https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=800&q=80" alt="Cable Pulldown" className="cd-gallery-img fade-up delay-1" />
          </div>
          <div className="cd-gallery-col">
             <img src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80" alt="Kettlebell" className="cd-gallery-img img-full fade-up delay-2" />
          </div>
          <div className="cd-gallery-col">
             <img src="https://images.unsplash.com/photo-1599058945522-28d584b6f4ff?auto=format&fit=crop&w=800&q=80" alt="Squat" className="cd-gallery-img fade-up delay-3" />
             <img src="https://images.unsplash.com/photo-1574680096145-d05b474e2155?auto=format&fit=crop&w=800&q=80" alt="Rope Pull" className="cd-gallery-img img-tall fade-up delay-4" />
          </div>
        </div>
      </section>

      {/* Related Classes */}
      <section className="cd-related-section container section">
        <div className="cd-related-header fade-up">
          <h2 className="cd-section-title">
            <span className="outline-text">YOU MAY ALSO</span><br/>
            INTERESTED IN
          </h2>
          <button className="btn-primary">VIEW MORE</button>
        </div>
        <div className="cd-related-grid">
          {relatedClasses.map((rc, idx) => (
            <div key={idx} className={`cd-related-card fade-up delay-${idx + 1}`}>
              <div className="cd-related-img-container">
                <img src={rc.img} alt={rc.title} className="cd-related-img" />
                <span className="cd-related-tag">{rc.level}</span>
                <div className="cd-related-info">
                  <h3>{rc.title}</h3>
                  <p>{rc.type}</p>
                </div>
                <div className="cd-book-now-tag">
                  BOOK NOW
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Banner */}
      <section className="cd-cta-section">
        <img 
          src="https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=2000&q=80" 
          alt="CTA Background" 
          className="cd-cta-img" 
        />
        <div className="cd-cta-overlay"></div>
        <div className="cd-cta-accent-shape"></div>
        <div className="container cd-cta-content">
          <h2 className="cd-cta-title fade-up">
            READY TO EXPERIENCE THE<br/>
            <span className="outline-text">INTENSITY AND VERSATILITY</span><br/>
            OF FITFUSION?
          </h2>
          <div className="fade-up delay-1 mt-4">
             <button className="btn-primary">SIGN UP FOR THE CLASS</button>
          </div>
        </div>
      </section>
    </div>
  );
}
