import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './Testimonials.css';

const testimonials = [
  {
    name: 'Joanne',
    role: 'Member since 2023',
    image: '/testimonial_woman.png',
    quote: '"Before joining VitroFit, I was stuck in a fitness rut. But the trainers here are amazing, and the community is so supportive! It\'s like a second home to me now."',
    stars: 5,
  },
  {
    name: 'Caleb',
    role: 'Member since 2022',
    image: '/testimonial_man.png',
    quote: '"I used to dread going to the gym, but VitroFit changed that for me. The variety of classes ensures I never get bored, and I genuinely look forward to each workout session!"',
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
