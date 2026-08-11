import { useState, useEffect } from 'react';
import './Timetable.css';

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const timeSlots = ["6:00 AM", "8:00 AM", "9:00 AM", "10:00 AM", "12:00 PM", "1:00 PM", "6:00 PM", "7:00 PM"];

const events = [
  { day: "Monday", time: "6:00 AM", title: "FITFUSION", trainer: "Alexandra Rodriguez" },
  { day: "Monday", time: "12:00 PM", title: "CARDIO KICK", trainer: "Emily Turner" },
  { day: "Monday", time: "7:00 PM", title: "YOGA HARMONY", trainer: "David Chen" },

  { day: "Tuesday", time: "8:00 AM", title: "YOGA HARMONY", trainer: "David Chen" },
  { day: "Tuesday", time: "9:00 AM", title: "FUNCTIONAL FITNESS", trainer: "Dr. Maya Patel" },
  { day: "Tuesday", time: "12:00 PM", title: "CYCLE FUSION", trainer: "Mark Johnson" },
  { day: "Tuesday", time: "7:00 PM", title: "STRENGTH SCULPT", trainer: "Mark Johnson" },

  { day: "Wednesday", time: "8:00 AM", title: "DANCE CARDIO GROOVE", trainer: "Sophie Nguyen" },
  { day: "Wednesday", time: "10:00 AM", title: "STRENGTH SCULPT", trainer: "Mark Johnson" },

  { day: "Thursday", time: "9:00 AM", title: "MINDFUL PILATES", trainer: "Sophie Nguyen", highlight: true },
  { day: "Thursday", time: "12:00 PM", title: "CARDIO KICK", trainer: "Emily Turner" },

  { day: "Friday", time: "6:00 AM", title: "FITFUSION", trainer: "Alexandra Rodriguez" },
  { day: "Friday", time: "10:00 AM", title: "YOGA HARMONY", trainer: "David Chen" },
  { day: "Friday", time: "12:00 PM", title: "CYCLE FUSION", trainer: "Mark Johnson" },
  { day: "Friday", time: "1:00 PM", title: "FITFUSION", trainer: "Mark Johnson" },

  { day: "Saturday", time: "8:00 AM", title: "YOGA HARMONY", trainer: "David Chen" },
  { day: "Saturday", time: "10:00 AM", title: "STRENGTH SCULPT", trainer: "Mark Johnson" },

  { day: "Sunday", time: "6:00 AM", title: "FITFUSION", trainer: "Alexandra Rodriguez" },
  { day: "Sunday", time: "10:00 AM", title: "DANCE CARDIO GROOVE", trainer: "Sophie Nguyen" },
  { day: "Sunday", time: "12:00 PM", title: "CARDIO KICK", trainer: "Emily Turner" },
  { day: "Sunday", time: "1:00 PM", title: "CYCLE FUSION", trainer: "Mark Johnson" },
  { day: "Sunday", time: "6:00 PM", title: "ZEN STRETCH", trainer: "Alexandra Rodriguez" },
  { day: "Sunday", time: "7:00 PM", title: "STRENGTH SCULPT", trainer: "Mark Johnson" },
];

const categories = ["ALL EVENTS", "FITFUSION", "CYCLE FUSION", "CARDIO KICK", "FUNCTIONAL FITNESS"];

const DumbbellIcon = () => (
  <svg width="24" height="12" viewBox="0 0 24 12" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="2" width="2" height="8" rx="1" />
    <rect x="4" y="0" width="4" height="12" rx="1" />
    <rect x="8" y="4" width="8" height="4" />
    <rect x="16" y="0" width="4" height="12" rx="1" />
    <rect x="22" y="2" width="2" height="8" rx="1" />
  </svg>
);

export default function Timetable() {
  const [activeCategory, setActiveCategory] = useState("ALL EVENTS");

  useEffect(() => {
    window.scrollTo(0, 0);

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.1 }
    );

    document.querySelectorAll('.fade-up, .fade-left, .fade-right').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="tt-page">
      {/* Hero Banner */}
      <section className="tt-hero">
        <img 
          src="https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=2000&q=80" 
          alt="Timetable Background" 
          className="tt-hero-img" 
        />
        <div className="tt-hero-overlay"></div>
        <div className="tt-hero-accent-shape"></div>
        <div className="container tt-hero-content">
          <div className="tt-breadcrumb fade-up">
            Home &gt; <span>Timetable</span>
          </div>
          <h1 className="tt-hero-title fade-up delay-1">
            YOUR DAILY <span className="outline-text">FITNESS</span><br/>
            <span className="outline-text">JOURNEY</span> STARTS HERE
          </h1>
        </div>
      </section>

      {/* Timetable Section */}
      <section className="tt-section container" id="timetable">
        {/* Tabs */}
        <div className="tt-tabs fade-up">
          <button className="tt-nav-btn">&lt;</button>
          {categories.map((cat) => (
            <button 
              key={cat}
              className={`tt-tab ${activeCategory === cat ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat)}
            >
              {cat}
            </button>
          ))}
          <button className="tt-nav-btn">&gt;</button>
        </div>

        {/* Grid */}
        <div className="tt-grid-wrapper fade-up delay-1">
          <div className="tt-grid">
            {/* Header Row */}
            <div className="tt-header-cell"></div> {/* Empty top-left cell */}
            {days.map(day => (
              <div key={day} className="tt-header-cell">{day}</div>
            ))}

            {/* Time Rows */}
            {timeSlots.map(time => (
              <div style={{display: 'contents'}} key={time}>
                <div className="tt-time-cell">{time}</div>
                {days.map(day => {
                  const event = events.find(e => e.day === day && e.time === time);
                  const isVisible = event && (activeCategory === "ALL EVENTS" || event.title === activeCategory);
                  
                  return (
                    <div key={`${day}-${time}`} className="tt-cell">
                      {isVisible && (
                        <div className={`tt-event ${event.highlight ? 'highlighted' : ''}`}>
                          <div className="tt-event-icon">
                            <DumbbellIcon />
                          </div>
                          <div className="tt-event-title">{event.title}</div>
                          <div className="tt-event-time">{event.time} - {
                            time === "6:00 AM" ? "7:00 AM" : 
                            time === "8:00 AM" ? "9:00 AM" : 
                            time === "9:00 AM" ? "10:00 AM" : 
                            time === "10:00 AM" ? "11:00 AM" : 
                            time === "12:00 PM" ? "1:00 PM" : 
                            time === "1:00 PM" ? "2:00 PM" : 
                            time === "6:00 PM" ? "7:00 PM" : 
                            time === "7:00 PM" ? "8:00 PM" : "Unknown"
                          }</div>
                          <div className="tt-event-trainer">{event.trainer}</div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="tt-cta">
        <img 
          src="https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=2000&q=80" 
          alt="CTA Background" 
          className="tt-cta-img" 
        />
        <div className="tt-cta-overlay"></div>
        <div className="tt-cta-accent-shape"></div>
        <div className="container tt-cta-content fade-up">
          <h2 className="tt-cta-title">
            <span className="outline-text">EXPLORE</span> OUR DIVERSE<br/>
            CLASS SCHEDULE
          </h2>
          <p className="tt-cta-desc">
            Join VitroFit today and enjoy a variety of classes throughout the day!
          </p>
          <div className="mt-4">
             <button className="btn-primary">VIEW FULL SCHEDULE</button>
          </div>
        </div>
      </section>
    </div>
  );
}
