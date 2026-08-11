import './index.css';
import Navbar from './components/Navbar/Navbar';
import Hero from './components/Hero/Hero';
import Classes from './components/Classes/Classes';
import Testimonials from './components/Testimonials/Testimonials';
import Pricing from './components/Pricing/Pricing';
import WhyUs from './components/WhyUs/WhyUs';
import Footer from './components/Footer/Footer';

export default function App() {
  return (
    <>
      <div className="noise-overlay" />
      <Navbar />
      <main>
        <Hero />
        <Classes />
        <Testimonials />
        <Pricing />
        <WhyUs />
      </main>
      <Footer />
    </>
  );
}
