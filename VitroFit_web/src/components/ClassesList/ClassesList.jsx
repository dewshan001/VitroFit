import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import './ClassesList.css';

const allClasses = [
  {
    title: "STRENGTH SCULPT",
    type: "Strength Training",
    level: "BEGINNER",
    img: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "CARDIO BURN",
    type: "Cardio & Endurance",
    level: "ALL LEVELS",
    img: "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "YOGA FLOW",
    type: "Yoga & Flexibility",
    level: "ALL LEVELS",
    img: "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "HOTEL GYM READY",
    type: "Minimal Equipment",
    level: "ALL LEVELS",
    img: "https://images.unsplash.com/photo-1594381898411-846e7d193883?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "HIIT BLAST",
    type: "High-Intensity Interval Training",
    level: "INTERMEDIATE",
    img: "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "OUTDOOR ATHLETE",
    type: "Bodyweight & Outdoor",
    level: "INTERMEDIATE",
    img: "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "ZEN & RECOVER",
    type: "Stretch & Relaxation",
    level: "ALL LEVELS",
    img: "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "POWER ATHLETE",
    type: "Advanced Strength",
    level: "ADVANCED",
    img: "https://images.unsplash.com/photo-1599058945522-28d584b6f4ff?auto=format&fit=crop&w=800&q=80"
  },
  {
    title: "FUNCTIONAL MOVE",
    type: "Functional Fitness",
    level: "ADVANCED",
    img: "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=800&q=80"
  }
];

export default function ClassesList() {
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
    <div className="classes-list-page">
      {/* Hero Banner */}
      <section className="cl-hero">
        <img 
          src="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=2000&q=80" 
          alt="Classes Hero Background" 
          className="cl-hero-img" 
        />
        <div className="cl-hero-overlay"></div>
        <div className="cl-hero-accent-shape"></div>
        <div className="container cl-hero-content">
          <div className="cl-breadcrumb fade-up">
            Home &gt; <span>Classes</span>
          </div>
          <h1 className="cl-hero-title fade-up delay-1">
            <span className="outline-text">YOUR WORKOUT PLANS,</span><br/>
            WHEREVER YOU GO
          </h1>
        </div>
      </section>

      {/* Classes Grid */}
      <section className="cl-grid-section container section">
        <div className="cl-grid">
          {allClasses.map((cls, idx) => (
            <div key={idx} className={`cl-card fade-up delay-${(idx % 3) + 1}`}>
              <div className="cl-img-container">
                <img src={cls.img} alt={cls.title} className="cl-img" />
                <span className="cl-tag">{cls.level}</span>
                <div className="cl-info">
                  <h3>{cls.title}</h3>
                  <p>{cls.type}</p>
                </div>
                <div className="cl-overlay">
                  <Link to="/classes/detail" className="cl-view-more-anim">
                    <span>VIEW MORE</span>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Banner */}
      <section className="cl-cta-section">
        <img 
          src="https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=2000&q=80" 
          alt="CTA Background" 
          className="cl-cta-img" 
        />
        <div className="cl-cta-overlay"></div>
        <div className="cl-cta-accent-shape"></div>
        <div className="container cl-cta-content fade-up">
          <h2 className="cl-cta-title">
            READY TO TRAIN <span className="outline-text">WITHOUT<br/>
            LIMITS?</span><br/>
            JOIN VITROFIT TODAY.
          </h2>
          <div className="cl-cta-btn-wrapper mt-4">
             <button className="btn-primary">START FOR FREE</button>
          </div>
        </div>
      </section>
    </div>
  );
}
