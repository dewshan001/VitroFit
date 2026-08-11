import { Routes, Route } from 'react-router-dom';
import './index.css';
import Navbar from './components/Navbar/Navbar';
import Footer from './components/Footer/Footer';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import ClassesPage from './pages/ClassesPage';
import ClassDetailPage from './pages/ClassDetailPage';
import TimetablePage from './pages/TimetablePage';

export default function App() {
  return (
    <>
      <div className="noise-overlay" />
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/classes" element={<ClassesPage />} />
        <Route path="/classes/detail" element={<ClassDetailPage />} />
        <Route path="/timetable" element={<TimetablePage />} />
      </Routes>
      <Footer />
    </>
  );
}
