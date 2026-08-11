import { useState, useEffect } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import './Navbar.css';

const navLinks = [
  { label: 'Home',      to: '/',       hash: '' },
  { label: 'About Us',  to: '/about',  hash: '' },
  { label: 'Classes',   to: '/classes',hash: '' },
  { label: 'Pricing',   to: '/',       hash: '#pricing' },
  { label: 'Timetable', to: '/timetable', hash: '' },
];

export default function Navbar() {
  const [scrolled, setScrolled]   = useState(false);
  const [menuOpen, setMenuOpen]   = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Scroll to top when route changes
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [location.pathname]);

  const handleNavClick = (link) => {
    setMenuOpen(false);
    if (link.hash) {
      if (location.pathname !== '/') {
        // Navigate home first, then scroll
        navigate('/');
        setTimeout(() => {
          document.querySelector(link.hash)?.scrollIntoView({ behavior: 'smooth' });
        }, 300);
      } else {
        document.querySelector(link.hash)?.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  const isActive = (link) => {
    if (link.hash) return false; // section links not highlighted as route-active
    return location.pathname === link.to;
  };

  return (
    <header className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <Link to="/" className="navbar-logo">
        <div className="navbar-logo-icon">V</div>
        <span className="navbar-logo-text">Vitro<span>Fit</span></span>
      </Link>

      <nav>
        <ul className={`navbar-nav ${menuOpen ? 'open' : ''}`}>
          {navLinks.map((link) => (
            <li key={link.label}>
              {link.hash ? (
                // Anchor links (Classes, Pricing, Timetable) — always on home page
                <a
                  href={location.pathname === '/' ? link.hash : undefined}
                  className={isActive(link) ? 'active' : ''}
                  onClick={() => handleNavClick(link)}
                >
                  {link.label}
                </a>
              ) : (
                // Real route links (Home, About Us)
                <Link
                  to={link.to}
                  className={isActive(link) ? 'active' : ''}
                  onClick={() => setMenuOpen(false)}
                >
                  {link.label}
                </Link>
              )}
            </li>
          ))}
        </ul>
      </nav>

      <div className="navbar-cta">
        <Link to="/login" className="btn-secondary navbar-login">Login</Link>
        <a href={location.pathname === '/' ? '#contact' : '/#contact'} className="btn-primary">Contact</a>
        <button
          className="navbar-hamburger"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <span style={{ transform: menuOpen ? 'rotate(45deg) translate(5px, 5px)' : 'none' }} />
          <span style={{ opacity: menuOpen ? 0 : 1 }} />
          <span style={{ transform: menuOpen ? 'rotate(-45deg) translate(5px, -5px)' : 'none' }} />
        </button>
      </div>
    </header>
  );
}
