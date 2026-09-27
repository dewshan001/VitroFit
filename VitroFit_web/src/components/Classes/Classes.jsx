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
  const { ref, isVisible } = useScrollAnimation();

  return (
    <section id="classes" className="section classes" ref={ref}>
      <div className="container">
        <div className={`classes-header fade-up ${isVisible ? 'visible' : ''}`}>
          <h2 className="section-title">
            <span className="classes-outline">EXPLORE</span> WORKOUT CATEGORIES
          </h2>
        </div>

        <div className="classes-carousel">
          <div className="classes-track-wrapper">
            <div className="classes-track">
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

        </div>
      </div>
    </section>
  );
}
