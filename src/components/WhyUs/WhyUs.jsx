import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './WhyUs.css';

const features = [
  {
    icon: '🎯',
    title: 'Personalized Training',
    desc: 'We create personalized workout plans designed specifically for your needs and goals, ensuring that every aspect of your fitness journey is customized to help you achieve success.',
  },
  {
    icon: '📅',
    title: 'Flexible Schedules',
    desc: 'Enjoy the flexibility of our fitness programs, offering early morning to late night classes, so you can choose the time that suits your schedule best.',
  },
  {
    icon: '⚡',
    title: 'Latest Equipment',
    desc: 'Stay ahead in your fitness journey with cutting-edge technology that not only enhances your workouts but also provides real-time data and analysis to help you track your progress.',
  },
  {
    icon: '🥗',
    title: 'Expert Nutritionists',
    desc: 'Our comprehensive fitness program goes beyond exercise; we also provide tailored meal plans to fuel your fitness journey. These nutritionally balanced meal plans are designed to support your specific fitness goals.',
  },
];

export default function WhyUs() {
  const { ref, isVisible } = useScrollAnimation();

  return (
    <section id="timetable" className="section why-us" ref={ref}>
      <div className="container">
        <div className="why-us-grid">
          {/* Left: Content */}
          <div>
            <h2 className={`why-us-title fade-left ${isVisible ? 'visible' : ''}`}>
              WHY <span className="accent">VITROFIT</span> IS YOUR<br />
              IDEAL FITNESS PARTNER
            </h2>

            <div className="features-list">
              {features.map((f, i) => (
                <div
                  key={f.title}
                  className={`feature-item fade-left delay-${i + 1} ${isVisible ? 'visible' : ''}`}
                >
                  <div className="feature-icon">{f.icon}</div>
                  <div>
                    <div className="feature-title">{f.title}</div>
                    <div className="feature-desc">{f.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Image */}
          <div className={`why-us-image-wrapper fade-right ${isVisible ? 'visible' : ''}`}>
            <img src="/battle_ropes.png" alt="Athlete training" className="why-us-image" />
            <div className="why-us-image-accent" />
            <div className="why-us-image-accent-2" />
            <div className="why-us-badge">
              <div className="why-us-badge-icon">🏆</div>
              <div className="why-us-badge-text">
                <strong>10+ Years</strong>
                <span>of Excellence</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
