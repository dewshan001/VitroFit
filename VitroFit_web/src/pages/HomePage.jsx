import Hero from '../components/Hero/Hero';
import Classes from '../components/Classes/Classes';
import Testimonials from '../components/Testimonials/Testimonials';
import Pricing from '../components/Pricing/Pricing';
import WhyUs from '../components/WhyUs/WhyUs';

export default function HomePage() {
  return (
    <main>
      <Hero />
      <Classes />
      <Testimonials />
      <Pricing />
      <WhyUs />
    </main>
  );
}
