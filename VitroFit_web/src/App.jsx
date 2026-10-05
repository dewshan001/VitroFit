import { Routes, Route, useLocation } from 'react-router-dom';
import AdaptiveFitnessPage from './features/adaptiveFitness/AdaptiveFitnessPage';
import './index.css';
import Navbar from './components/Navbar/Navbar';
import Footer from './components/Footer/Footer';
import Chatbot from './components/Chatbot/Chatbot';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import TimetablePage from './pages/TimetablePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import RegisterGymPage from './pages/RegisterGymPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ProfilePage from './pages/ProfilePage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import GymApprovalsPage from './pages/GymApprovalsPage';
import FindGymsPage from './pages/FindGymsPage';
import DietPlansPage from './pages/DietPlansPage';

const AUTH_ROUTES = ['/login', '/register', '/register-gym'];

export default function App() {
  const { pathname } = useLocation();
  const isAuthPage = AUTH_ROUTES.includes(pathname);

  return (
    <>
      <div className="noise-overlay" />
      {!isAuthPage && <Navbar />}
      <Routes>
        <Route path="/adaptive-fitness" element={<AdaptiveFitnessPage />} />
        <Route path="/"               element={<HomePage />} />
        <Route path="/about"          element={<AboutPage />} />
        <Route path="/timetable"      element={<TimetablePage />} />
        <Route path="/find-gyms"      element={<FindGymsPage />} />
        <Route path="/diet-plans"     element={<DietPlansPage />} />
        <Route path="/login"          element={<LoginPage />} />
        <Route path="/register"       element={<RegisterPage />} />
        <Route path="/register-gym"   element={<RegisterGymPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/profile"        element={<ProfilePage />} />
        <Route path="/admin"          element={<AdminDashboardPage />} />
        <Route path="/admin/gym-approvals" element={<GymApprovalsPage />} />
      </Routes>
      {!isAuthPage && <Chatbot />}
      {!isAuthPage && <Footer />}
    </>
  );
}
