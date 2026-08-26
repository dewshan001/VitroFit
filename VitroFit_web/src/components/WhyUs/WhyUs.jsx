import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './WhyUs.css';

const features = [
  {
    icon: '🗺️',
    title: 'Find Gyms Anywhere',
    desc: 'Instantly locate verified partner gyms near your location, whether you are at home or on the other side of the world. Filter by equipment, price, and opening hours.',
  },
  {
    icon: '📋',
    title: 'Sync Your Workout Plan',
    desc: 'Your custom workout plans travel with you. Access them from any device, edit on the fly, and always know exactly what your next session looks like.',
  },
  {
    icon: '📅',
    title: 'Smart Timetable',
    desc: 'Organize your weekly workout schedule and get reminders. Reschedule sessions with a tap when travel plans change — your consistency stays intact.',
  },
  {
    icon: '📊',
    title: 'Progress Tracking',
    desc: 'Log your workouts across different gyms and track your progress over time. See how far you have come, no matter where you trained.',
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
              IDEAL FITNESS COMPANION
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
              <div className="why-us-badge-icon">🌍</div>
              <div className="why-us-badge-text">
                <strong>5,000+</strong>
                <span>Partner Gyms</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
