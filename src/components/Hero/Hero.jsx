import { useEffect, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, Float, Ring, Torus } from '@react-three/drei';
import * as THREE from 'three';
import './Hero.css';

// 3D Floating orb with distortion
function FloatingOrb({ position, scale, color, speed, distort }) {
  const meshRef = useRef();
  useFrame(({ clock }) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = clock.getElapsedTime() * 0.2 * speed;
      meshRef.current.rotation.y = clock.getElapsedTime() * 0.3 * speed;
    }
  });
  return (
    <Float speed={speed} rotationIntensity={0.5} floatIntensity={0.8}>
      <Sphere ref={meshRef} args={[1, 64, 64]} position={position} scale={scale}>
        <MeshDistortMaterial
          color={color}
          attach="material"
          distort={distort}
          speed={2}
          roughness={0.2}
          metalness={0.8}
          transparent
          opacity={0.15}
        />
      </Sphere>
    </Float>
  );
}

// 3D Ring
function FloatingRing({ position, rotation, scale, color }) {
  const ringRef = useRef();
  useFrame(({ clock }) => {
    if (ringRef.current) {
      ringRef.current.rotation.x = clock.getElapsedTime() * 0.15;
      ringRef.current.rotation.z = clock.getElapsedTime() * 0.1;
    }
  });
  return (
    <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.5}>
      <Torus ref={ringRef} args={[1, 0.04, 16, 100]} position={position} rotation={rotation} scale={scale}>
        <meshBasicMaterial color={color} transparent opacity={0.3} />
      </Torus>
    </Float>
  );
}

// Particle field
function Particles({ count = 80 }) {
  const points = useRef();
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 20;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
  }

  useFrame(({ clock }) => {
    if (points.current) {
      points.current.rotation.y = clock.getElapsedTime() * 0.02;
    }
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial color="#c8f000" size={0.04} transparent opacity={0.6} sizeAttenuation />
    </points>
  );
}

// Stats counter animation
function StatCounter({ end, suffix = '', duration = 2000 }) {
  const ref = useRef(null);
  useEffect(() => {
    let start = 0;
    const step = end / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= end) {
        start = end;
        clearInterval(timer);
      }
      if (ref.current) {
        ref.current.textContent = Math.floor(start) + suffix;
      }
    }, 16);
    return () => clearInterval(timer);
  }, [end, suffix, duration]);
  return <span ref={ref}>0{suffix}</span>;
}

const stats = [
  { number: 500, suffix: '+', label: 'Happy Members', desc: 'Our community is growing fast!' },
  { number: 30, suffix: '+', label: 'Weekly Classes', desc: 'Pick from various workouts' },
  { number: 10, suffix: '', label: 'Certified Trainers', desc: 'Guidance at every step.' },
  { number: 99, suffix: '%', label: 'Customer Satisfaction', desc: 'We ensure your progress satisfaction' },
];

export default function Hero() {
  const sectionRef = useRef(null);
  const titleRef = useRef(null);
  const subtitleRef = useRef(null);
  const buttonsRef = useRef(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (titleRef.current) titleRef.current.style.opacity = 1, titleRef.current.style.transform = 'translateY(0)';
    }, 100);
    const timer2 = setTimeout(() => {
      if (subtitleRef.current) subtitleRef.current.style.opacity = 1, subtitleRef.current.style.transform = 'translateY(0)';
    }, 300);
    const timer3 = setTimeout(() => {
      if (buttonsRef.current) buttonsRef.current.style.opacity = 1, buttonsRef.current.style.transform = 'translateY(0)';
    }, 500);
    return () => { clearTimeout(timer); clearTimeout(timer2); clearTimeout(timer3); };
  }, []);

  return (
    <section id="home" className="hero" ref={sectionRef}>
      {/* 3D Canvas Background */}
      <div className="hero-canvas">
        <Canvas camera={{ position: [0, 0, 5], fov: 75 }}>
          <ambientLight intensity={0.2} />
          <pointLight position={[5, 5, 5]} color="#c8f000" intensity={1.5} />
          <pointLight position={[-5, -5, 3]} color="#ffffff" intensity={0.3} />
          <FloatingOrb position={[-4, 2, -2]} scale={2.5} color="#c8f000" speed={0.5} distort={0.4} />
          <FloatingOrb position={[3, -1, -3]} scale={1.5} color="#9ab800" speed={0.8} distort={0.6} />
          <FloatingOrb position={[5, 3, -4]} scale={3} color="#c8f000" speed={0.3} distort={0.3} />
          <FloatingRing position={[-2, -2, -2]} rotation={[0.5, 0.3, 0]} scale={2} color="#c8f000" />
          <FloatingRing position={[4, 0, -3]} rotation={[0.2, 0.8, 0.5]} scale={1.5} color="#ffffff" />
          <Particles count={100} />
        </Canvas>
      </div>

      {/* Hero Image */}
      <img src="/hero_athlete.png" alt="VitroFit Athlete" className="hero-bg-image" />
      <div className="hero-bg-gradient" />
      <div className="hero-bottom-gradient" />
      <div className="hero-diagonal" />

      {/* Content */}
      <div className="hero-content">
        <div
          className="hero-eyebrow"
          style={{ opacity: 0, transform: 'translateY(20px)', transition: 'all 0.6s ease 0s' }}
          ref={(el) => { if (el) setTimeout(() => { el.style.opacity = 1; el.style.transform = 'translateY(0)'; }, 50); }}
        >
          <div className="hero-eyebrow-line" />
          <span className="hero-eyebrow-text">Elite Fitness Studio</span>
        </div>

        <h1
          className="hero-title"
          ref={titleRef}
          style={{ opacity: 0, transform: 'translateY(40px)', transition: 'all 0.8s ease' }}
        >
          <span className="outline-text">ACHIEVE</span> MORE<br />
          THAN JUST FITNESS
        </h1>

        <p
          className="hero-subtitle"
          ref={subtitleRef}
          style={{ opacity: 0, transform: 'translateY(30px)', transition: 'all 0.8s ease' }}
        >
          Combine strength, flexibility, and endurance in a community that values well-rounded health and supportive growth.
        </p>

        <div
          className="hero-buttons"
          ref={buttonsRef}
          style={{ opacity: 0, transform: 'translateY(20px)', transition: 'all 0.8s ease' }}
        >
          <a href="#classes" className="btn-primary">START NOW</a>
          <a href="#pricing" className="btn-secondary">JOIN FREE TRIAL</a>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="hero-stats">
        <div className="hero-stats-grid">
          {stats.map((stat, i) => (
            <div className="hero-stat-item" key={i}>
              <div className="hero-stat-number">
                <StatCounter end={stat.number} suffix={stat.suffix} duration={2000} />
              </div>
              <div className="hero-stat-label">{stat.label}</div>
              <div className="hero-stat-desc">{stat.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
