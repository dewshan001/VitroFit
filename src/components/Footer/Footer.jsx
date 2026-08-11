import './Footer.css';

export default function Footer() {
  return (
    <footer id="contact" className="footer">
      <div className="container">
        <div className="footer-grid">
          {/* Brand */}
          <div>
            <a href="#home" className="footer-brand-logo">
              <div className="footer-brand-icon">V</div>
              <span className="footer-brand-name">Vitro<span>Fit</span></span>
            </a>
            <p className="footer-tagline">
              Combine strength, flexibility, and endurance in a community that values well-rounded health and supportive growth.
            </p>
            <div className="footer-socials">
              <a href="#" className="footer-social-btn" aria-label="Facebook">f</a>
              <a href="#" className="footer-social-btn" aria-label="Instagram">ig</a>
              <a href="#" className="footer-social-btn" aria-label="Twitter">tw</a>
              <a href="#" className="footer-social-btn" aria-label="YouTube">yt</a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="footer-heading">Quick Links</h4>
            <ul className="footer-links">
              <li><a href="#home">Home</a></li>
              <li><a href="#about">About Us</a></li>
              <li><a href="#classes">Classes</a></li>
              <li><a href="#pricing">Pricing</a></li>
              <li><a href="#timetable">Timetable</a></li>
            </ul>
          </div>

          {/* Programs */}
          <div>
            <h4 className="footer-heading">Programs</h4>
            <ul className="footer-links">
              <li><a href="#classes">Strength Training</a></li>
              <li><a href="#classes">Cardio Blast</a></li>
              <li><a href="#classes">Yoga & Flexibility</a></li>
              <li><a href="#classes">Nutrition & Diet</a></li>
              <li><a href="#classes">Personal Training</a></li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="footer-heading">Contact Us</h4>
            <div className="footer-contact-item">
              <span className="footer-contact-icon">📍</span>
              <span>123 Fitness Ave, Colombo 07, Sri Lanka</span>
            </div>
            <div className="footer-contact-item">
              <span className="footer-contact-icon">📞</span>
              <span>+94 11 234 5678</span>
            </div>
            <div className="footer-contact-item">
              <span className="footer-contact-icon">✉️</span>
              <span>hello@vitrofit.lk</span>
            </div>
            <div className="footer-contact-item">
              <span className="footer-contact-icon">⏰</span>
              <span>Mon–Sat: 5:00 AM – 11:00 PM</span>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <p className="footer-copyright">
            © 2026 <span>VitroFit</span>. All rights reserved. Designed with ❤️
          </p>
          <div className="footer-bottom-links">
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Cookie Policy</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
