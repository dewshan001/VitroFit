import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './Testimonials.css';

const testimonials = [
  {
    name: 'Joanne',
    role: 'VitroFit Pro Member',
    image: '/testimonial_woman.png',
    quote: '"I travel for work almost every week. Before VitroFit, my workouts would fall apart the moment I left home. Now I just open the app, find a gym nearby, and follow my plan as if I never left."',
    stars: 5,
  },
  {
    name: 'Caleb',
    role: 'VitroFit Elite Member',
    image: '/testimonial_man.png',
    quote: '"The timetable feature is a game changer. I plan my workouts for the whole week, and when my schedule shifts while traveling, I just drag and reschedule. My consistency has never been better!"',
    stars: 5,
  },
];

export default function Testimonials() {
  const { ref, isVisible } = useScrollAnimation();

  return (
    <section id="about" className="section transformations" ref={ref}>
      <div className="container">
        <div className={`transformations-header fade-up ${isVisible ? 'visible' : ''}`}>
          <h2 className="transformations-title">
            TRANSFORMATIONS SPEAK<br />
            LOUDER <span className="thin">THAN WORDS</span>
          </h2>
          <a href="#contact" className="btn-primary transformations-view-btn">VIEW MORE</a>
        </div>

        <div className="testimonials-grid">
          {testimonials.map((t, i) => (
            <div
              key={t.name}
              className={`testimonial-card fade-up delay-${i + 1} ${isVisible ? 'visible' : ''}`}
            >
              <img src={t.image} alt={t.name} className="testimonial-image" />
              <div className="testimonial-body">
                <p className="testimonial-quote">{t.quote}</p>
                <div className="testimonial-stars">
                  {Array.from({ length: t.stars }).map((_, j) => (
                    <span key={j}>★</span>
                  ))}
                </div>
                <div className="testimonial-name">{t.name}</div>
                <div className="testimonial-role">{t.role}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
