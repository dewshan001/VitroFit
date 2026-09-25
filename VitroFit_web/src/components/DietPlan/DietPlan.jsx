import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import DietPlanPreferenceForm from './DietPlanPreferenceForm';
import DietPlanResult from './DietPlanResult';
import {
  generateDietPlan,
  confirmDietPlan,
  updateDietPlan,
  deleteDietPlan,
  fetchSavedDietPlans,
} from '../../api/dietPlan';
import './DietPlan.css';

// Real hero for the page banner.
const HERO_IMG =
  'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=2000&q=80';

export default function DietPlan() {
  const { auth, getFullName } = useAuth();
  const user = auth?.user ?? {};

  // phase: 'loading-plans' | 'browse' | 'empty' | 'form' | 'loading' | 'result' | 'error' | 'view'
  const [phase, setPhase] = useState('loading-plans');
  const [plan, setPlan] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [confirmStatus, setConfirmStatus] = useState('idle'); // idle | saving | saved | error
  const [confirmErrorMessage, setConfirmErrorMessage] = useState('');
  const [savedPlans, setSavedPlans] = useState([]);
  const [viewingPlan, setViewingPlan] = useState(null);
  const [editingPlanId, setEditingPlanId] = useState(null);

  // Prefill from existing profile where available (goal + level).
  const initialPrefs = {
    age: user.age ?? 25,
    gender: user.gender ?? 'male',
    heightCm: user.heightCm ?? 175,
    weightKg: user.weightKg ?? 70,
    activityLevel: mapActivityFromLevel(user.level) ?? 'moderate',
    goal: user.goal ?? 'maintenance',
    mealFrequency: '3Meals',
    restrictions: [],
    dislikes: user.dislikes ?? '',
    budgetTier: 'medium',
    budgetCustomAmount: null,
    medicalConditions: [],
    cookingTime: 'moderate',
  };

  // Remembers the most recently used preferences for Regenerate/Confirm.
  const [lastPrefs, setLastPrefs] = useState(initialPrefs);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add('visible');
        });
      },
      { threshold: 0.1 }
    );
    document
      .querySelectorAll('.dp-fade-up')
      .forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [phase]);

  const refreshSavedPlans = async () => {
    if (!auth) return [];
    try {
      const plans = await fetchSavedDietPlans();
      setSavedPlans(plans);
      return plans;
    } catch {
      return savedPlans;
    }
  };

  // Initial load: once the saved plans come back, land on Browse (if any exist)
  // or Empty (first-time user). Later refreshes (after confirm/update/delete)
  // don't re-navigate — they just keep the list current.
  useEffect(() => {
    if (!auth) return;
    let cancelled = false;
    (async () => {
      const plans = await refreshSavedPlans();
      if (cancelled) return;
      setPhase((prev) => (prev === 'loading-plans' ? (plans.length > 0 ? 'browse' : 'empty') : prev));
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth]);

  const handleGenerate = async (prefs) => {
    setPhase('loading');
    setConfirmStatus('idle');
    try {
      const result = await generateDietPlan(toApiPrefs(prefs));
      setPlan(result);
      setPhase('result');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setErrorMessage(err.message || 'Something went wrong while generating your diet plan.');
      setPhase('error');
    }
  };

  const handleEdit = () => setPhase('form');

  const handleCancelEdit = () => {
    if (editingPlanId) {
      setEditingPlanId(null);
      setPhase('browse');
    } else {
      setPhase('result');
    }
  };

  const runGenerate = (prefs) => {
    setLastPrefs(prefs);
    handleGenerate(prefs);
  };

  const handleConfirm = async () => {
    if (!plan) return;
    if (!auth) {
      setConfirmErrorMessage('Please log in to save your plan.');
      setConfirmStatus('error');
      return;
    }
    setConfirmStatus('saving');
    try {
      if (editingPlanId) {
        await updateDietPlan(editingPlanId, toApiPrefs(lastPrefs), plan);
      } else {
        await confirmDietPlan(toApiPrefs(lastPrefs), plan);
      }
      setConfirmStatus('saved');
      setConfirmErrorMessage('');
      await refreshSavedPlans();
    } catch (err) {
      setConfirmErrorMessage(err.message || "Couldn't save your plan. Please try again.");
      setConfirmStatus('error');
    }
  };

  const handleCreateNew = () => {
    setPlan(null);
    setEditingPlanId(null);
    setLastPrefs(initialPrefs);
    setConfirmStatus('idle');
    setConfirmErrorMessage('');
    setPhase('form');
  };

  const handleViewPlan = (savedPlan) => {
    setViewingPlan(savedPlan);
    setPhase('view');
  };

  const handleEditSavedPlan = (savedPlan) => {
    setEditingPlanId(savedPlan.id);
    setLastPrefs(savedPlan.inputs || initialPrefs);
    setPlan(null);
    setConfirmStatus('idle');
    setConfirmErrorMessage('');
    setPhase('form');
  };

  const handleBackToBrowse = () => {
    setViewingPlan(null);
    setPhase(savedPlans.length > 0 ? 'browse' : 'empty');
  };

  const handleDeletePlan = async (planId) => {
    if (!window.confirm('Delete this diet plan? This cannot be undone.')) return;
    try {
      await deleteDietPlan(planId);
      const plans = await refreshSavedPlans();
      if (viewingPlan?.id === planId) setViewingPlan(null);
      setPhase(plans.length > 0 ? 'browse' : 'empty');
    } catch {
      window.alert("Couldn't delete this plan. Please try again.");
    }
  };

  return (
    <div className="diet-plan-page">
      <section className="dp-hero">
        <img src={HERO_IMG} alt="Healthy food bowl" className="dp-hero-img" />
        <div className="dp-hero-overlay" />
        <div className="dp-hero-accent-shape" />
        <div className="container dp-hero-content">
          <div className="dp-breadcrumb dp-fade-up">
            Home &gt; <span>Diet Plans</span>
          </div>
          <div className="dp-hero-eyebrow dp-fade-up dp-d1">
            <div className="dp-hero-eyebrow-line" />
            <span className="dp-hero-eyebrow-text">VitroFit AI Nutrition</span>
          </div>
          <h1 className="dp-hero-title dp-fade-up dp-d2">
            <span className="outline-text">PERSONALISED</span> DIET<br />
            PLANS FOR YOUR GOALS
          </h1>
          <p className="dp-hero-sub dp-fade-up dp-d3">
            Tell us about your body, goals, and preferences to get
            {getFullName() ? ` a plan tailored for ${getFullName()}` : ' a tailored'} plan —
            built meal by meal with realistic portions and macros.
          </p>
        </div>
      </section>

      <section className="dp-section">
        <div className="container">
          {!auth && (
            <div className="dp-empty dp-fade-up">
              <div className="dp-empty-icon">🔒</div>
              <h2 className="dp-empty-title">Log In to Build Your Diet Plan</h2>
              <p className="dp-empty-desc">
                Create an account or log in so we can generate and save a personalised
                nutrition plan under your profile.
              </p>
              <Link to="/login" className="btn-primary">Log In</Link>
            </div>
          )}

          {auth && phase === 'loading-plans' && (
            <div className="dp-loading dp-fade-up">
              <div className="dp-loading-top">
                <span className="dp-loader" />
                <h3 className="dp-loading-title">Loading your plans…</h3>
              </div>
            </div>
          )}

          {auth && phase === 'browse' && (
            <DietPlanResult
              state="browse"
              savedPlans={savedPlans}
              onCreateNew={handleCreateNew}
              onViewPlan={handleViewPlan}
              onEditPlan={handleEditSavedPlan}
              onDeletePlan={handleDeletePlan}
            />
          )}

          {auth && phase === 'empty' && <DietPlanResult state="empty" onGenerate={handleCreateNew} />}

          {auth && phase === 'form' && (
            <DietPlanPreferenceForm
              initialPrefs={lastPrefs}
              onSubmit={runGenerate}
              onCancel={(plan || editingPlanId) ? handleCancelEdit : undefined}
            />
          )}

          {auth && phase === 'loading' && <DietPlanResult state="loading" />}

          {auth && phase === 'error' && (
            <DietPlanResult
              state="error"
              errorMessage={errorMessage}
              onEdit={handleEdit}
              onRegenerate={() => runGenerate(lastPrefs)}
            />
          )}

          {auth && phase === 'result' && plan && (
            <DietPlanResult
              state="result"
              plan={plan}
              hasMedicalConditions={(lastPrefs.medicalConditions || []).length > 0}
              confirmStatus={confirmStatus}
              confirmErrorMessage={confirmErrorMessage}
              onEdit={handleEdit}
              onConfirm={handleConfirm}
              onBack={handleBackToBrowse}
            />
          )}

          {auth && phase === 'view' && viewingPlan && (
            <DietPlanResult
              state="view"
              plan={viewingPlan}
              hasMedicalConditions={(viewingPlan.inputs?.medicalConditions || []).length > 0}
              onBack={handleBackToBrowse}
              onEdit={() => handleEditSavedPlan(viewingPlan)}
              onDelete={() => handleDeletePlan(viewingPlan.id)}
            />
          )}
        </div>
      </section>

      <section className="dp-cta">
        <img
          src="https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=2000&q=80"
          alt="Healthy meal ingredients"
          className="dp-cta-img"
        />
        <div className="dp-cta-overlay" />
        <div className="dp-cta-accent-shape" />
        <div className="container dp-cta-content dp-fade-up">
          <h2 className="dp-cta-title">
            <span className="outline-text">EAT SMART</span>, TRAIN
            <br />
            WITHOUT LIMITS
          </h2>
          <p className="dp-cta-desc">
            Combine your personalised meal plan with your workout schedule and
            partner gyms on VitroFit — sustain your energy wherever you train.
          </p>
        </div>
      </section>
    </div>
  );
}
/* ──────────────────────────────────────────────
   HELPERS
────────────────────────────────────────────── */

/** Map an existing profile `level` to an activity factor key (reuse profile data). */
function mapActivityFromLevel(level) {
  if (!level) return null;
  const l = String(level).toLowerCase();
  if (l.includes('beginner') || l.includes('lightly')) return 'light';
  if (l.includes('advanced') || l.includes('highly')) return 'active';
  if (l.includes('intermediate')) return 'moderate';
  return null;
}

/** Maps the form's preference shape to DietPlanService's expected request body. */
function toApiPrefs(prefs) {
  return {
    age: prefs.age,
    gender: prefs.gender,
    heightCm: prefs.heightCm,
    weightKg: prefs.weightKg,
    activityLevel: prefs.activityLevel,
    goal: prefs.goal,
    mealFrequency: prefs.mealFrequency,
    restrictions: prefs.restrictions,
    dislikes: prefs.dislikes,
    budgetTier: prefs.budgetTier,
    budgetCustomAmount: prefs.budgetTier === 'custom' ? prefs.budgetCustomAmount : null,
    medicalConditions: prefs.medicalConditions,
    cookingTime: prefs.cookingTime,
  };
}
