import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './Pricing.css';

const plans = [
  {
    tier: 'Free Plan',
    price: 0,
    frequency: 'FOREVER FREE',
    features: [
      'Find up to 5 nearby gyms',
      'Access 3 pre-built workout plans',
      'Basic timetable management',
    ],
  },
  {
    tier: 'Pro Plan',
    price: 1490,
    frequency: 'PER MONTH',
    featured: true,
    features: [
      'Unlimited gym discovery worldwide',
      'Create & sync custom workout plans',
      'Full timetable with reminders',
      'Progress tracking & analytics',
    ],
  },
  {
    tier: 'Elite Plan',
    price: 2990,
    frequency: 'PER MONTH',
    features: [
      'All Pro Plan features',
      'Priority gym check-in access',
      'AI-powered workout recommendations',
      'Dedicated travel fitness coach',
    ],
  },
];

export default function Pricing() {
  const { ref, isVisible } = useScrollAnimation();

  return (
    <section id="pricing" className="section pricing" ref={ref}>
      <div className="container">
        <div className={`pricing-header fade-up ${isVisible ? 'visible' : ''}`}>
          <h2 className="section-title">
            FLEXIBLE <span className="accent">PLANS FOR</span><br />
            EVERY FITNESS JOURNEY
          </h2>
        </div>
        <p className={`pricing-subtitle fade-up delay-1 ${isVisible ? 'visible' : ''}`}>
          Start free, upgrade when you're ready. No long-term commitments, cancel anytime.
        </p>

        <div className="pricing-grid">
          {plans.map((plan, i) => (
            <div
              key={plan.tier}
              className={`pricing-card fade-up delay-${i + 2} ${isVisible ? 'visible' : ''} ${plan.featured ? 'featured' : ''}`}
            >
              <div className="pricing-tier">{plan.tier}</div>
              <div className="pricing-price">
                <span className="pricing-currency">{plan.price === 0 ? '' : 'Rs. '}</span>
                <span className="pricing-amount">{plan.price === 0 ? 'Free' : plan.price}</span>
                <span className="pricing-period">{plan.price === 0 ? '' : '/month'}</span>
              </div>
              <div className="pricing-frequency">{plan.frequency}</div>

              <ul className="pricing-features">
                {plan.features.map((f) => (
                  <li key={f}>
                    <span className="pricing-check">✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button className="pricing-btn">GET STARTED</button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
