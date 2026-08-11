import { useScrollAnimation } from '../../hooks/useScrollAnimation';
import './Pricing.css';

const plans = [
  {
    tier: 'Basic Plan',
    price: 3900,
    frequency: '3 DAYS/WEEK',
    features: [
      'Access to all cardio classes',
      'Monthly body assessment',
      'Nutritional guidance',
    ],
  },
  {
    tier: 'Premium Plan',
    price: 5900,
    frequency: '3 DAYS/WEEK',
    featured: true,
    features: [
      'All Basic Plan features',
      'Strength training sessions',
      'Nutritional guidance',
    ],
  },
  {
    tier: 'Elite Plan',
    price: 8900,
    frequency: '3 DAYS/WEEK',
    features: [
      'All Premium Plan features',
      'Personal training session once a month',
      'Priority booking for all classes',
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
            EVERY BUDGET
          </h2>
        </div>
        <p className={`pricing-subtitle fade-up delay-1 ${isVisible ? 'visible' : ''}`}>
          Choose a plan that suits you. No long-term commitments required.
        </p>

        <div className="pricing-grid">
          {plans.map((plan, i) => (
            <div
              key={plan.tier}
              className={`pricing-card fade-up delay-${i + 2} ${isVisible ? 'visible' : ''} ${plan.featured ? 'featured' : ''}`}
            >
              <div className="pricing-tier">{plan.tier}</div>
              <div className="pricing-price">
                <span className="pricing-currency">Rs. </span>
                <span className="pricing-amount">{plan.price}</span>
                <span className="pricing-period">/month</span>
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
