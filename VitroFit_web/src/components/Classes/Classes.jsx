import { useState, useRef } from 'react';
import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './Classes.css';

const classes = [
  {
    id: 1,
    title: 'Strength Training',
    category: 'Power',
    desc: 'Build muscle and increase stamina with guided strength plans.',
    image: '/strength_training.png',
    active: true,
  },
  {
    id: 2,
    title: 'Cardio & Endurance',
    category: 'Endurance',
    desc: 'Maximize heart health and burn calories anywhere.',
    image: '/cardio_blast.png',
  },
  {
    id: 3,
    title: 'Yoga & Flexibility',
    category: 'Wellness',
    desc: 'Achieve mental clarity and body flexibility on the go.',
    image: '/yoga_flexibility.png',
  },
  {
    id: 4,
    title: 'Hotel Gym Ready',
    category: 'Travel',
    desc: 'Compact, equipment-light plans perfect for hotel gyms.',
    image: '/battle_ropes.png',
  },
];

export default function Classes() {
  const [activeIndex, setActiveIndex] = useState(0);
  const trackRef = useRef(null);
  const { ref, isVisible } = useScrollAnimation();

  const goTo = (index) => {
    setActiveIndex(index);
    if (trackRef.current) {
      const cardWidth = trackRef.current.children[0]?.offsetWidth + 24;
      trackRef.current.style.transform = `translateX(-${index * cardWidth}px)`;
    }
  };

  const prev = () => goTo(Math.max(0, activeIndex - 1));
  const next = () => goTo(Math.min(classes.length - 1, activeIndex + 1));

  return (
    <section id="classes" className="section classes" ref={ref}>
      <div className="container">
        <div className={`classes-header fade-up ${isVisible ? 'visible' : ''}`}>
          <h2 className="section-title">
            <span className="classes-outline">EXPLORE</span> WORKOUT CATEGORIES
          </h2>
        </div>

        <div className={`classes-nav fade-up delay-1 ${isVisible ? 'visible' : ''}`}>
          <button className="classes-nav-btn" onClick={prev} aria-label="Previous">&#8592;</button>
          <button className="classes-nav-btn" onClick={next} aria-label="Next">&#8594;</button>
        </div>

        <div className="classes-carousel">
          <div className="classes-track-wrapper">
            <div className="classes-track" ref={trackRef}>
              {classes.map((cls, i) => (
                <div className="class-card" key={cls.id}>
                  <img src={cls.image} alt={cls.title} className="class-card-image" />
                  <button className="class-card-view-btn">VIEW MORE</button>
                  <div className="class-card-accent" />
                  <div className="class-card-overlay">
                    <div className="class-card-category">{cls.category}</div>
                    <div className={`class-card-title ${cls.active ? '' : 'no-underline'}`}>{cls.title}</div>
                    <div className="class-card-desc">{cls.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="classes-indicators">
            {classes.map((_, i) => (
              <button
                key={i}
                className={`classes-indicator ${i === activeIndex ? 'active' : ''}`}
                onClick={() => goTo(i)}
                aria-label={`Go to slide ${i + 1}`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
