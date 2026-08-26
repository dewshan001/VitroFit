import './Footer.css';

export default function Footer() {
  return (
    <footer id="contact" className="footer">
      <div className="container">
        <div className="footer-grid">
          {/* About */}
          <div className="footer-col">
            <h4 className="footer-heading">Platform</h4>
            <ul className="footer-links">
              <li><a href="#about">How It Works</a></li>
              <li><a href="#about">Our Mission</a></li>
              <li><a href="#about">Meet the Team</a></li>
              <li><a href="#about">Careers</a></li>
              <li><a href="#about">FAQs</a></li>
            </ul>
          </div>

          {/* Contact */}
          <div className="footer-col">
            <h4 className="footer-heading">Contact</h4>
            <ul className="footer-links">
              <li><a href="#contact">Contact Us</a></li>
              <li><a href="#contact">Support</a></li>
              <li><a href="#contact">Partner with Us</a></li>
              <li><a href="#contact">Gym Partnerships</a></li>
            </ul>
          </div>

          {/* Features */}
          <div className="footer-col">
            <h4 className="footer-heading">Features</h4>
            <ul className="footer-links">
              <li><a href="#classes">Find Gyms</a></li>
              <li><a href="#classes">Workout Plans</a></li>
              <li><a href="#timetable">Timetable</a></li>
              <li><a href="#classes">Progress Tracker</a></li>
            </ul>
          </div>

          {/* Resources */}
          <div className="footer-col">
            <h4 className="footer-heading">Resources</h4>
            <ul className="footer-links">
              <li><a href="#resources">Blog</a></li>
              <li><a href="#resources">Travel Fitness Tips</a></li>
              <li><a href="#resources">Workout Guides</a></li>
              <li><a href="#resources">App Download</a></li>
            </ul>
          </div>

          {/* Newsletter */}
          <div className="footer-col footer-newsletter-col">
            <h4 className="footer-heading">Sign up for our newsletter</h4>
            <form className="footer-newsletter-form" onSubmit={(e) => e.preventDefault()}>
              <input type="email" placeholder="Email Address" required />
              <button type="submit" className="btn-primary">SUBSCRIBE</button>
            </form>
            <div className="footer-socials-new">
              <a href="#" className="social-icon" aria-label="Instagram">ig</a>
              <a href="#" className="social-icon" aria-label="Twitter">tw</a>
              <a href="#" className="social-icon" aria-label="YouTube">yt</a>
              <a href="#" className="social-icon" aria-label="LinkedIn">in</a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
