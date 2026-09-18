// VitroFit_web/src/pages/FitnessAgentPage.jsx
import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import {
  getFitnessProfile,
  saveFitnessProfile,
  startFitnessWorkflow,
  getCurrentWorkoutPlan,
  logWorkoutProgress,
  generateNextSchedule,
  getWorkflowHistory,
  getPendingApprovals,
  reviewWorkflowPlan
} from '../api/fitness';
import './FitnessAgentPage.css';

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function FitnessAgentPage() {
  const { isLoggedIn, user } = useAuth();
  const [activeTab, setActiveTab] = useState('plan'); // 'plan' | 'profile' | 'progress' | 'history' | 'approvals'
  const [loading, setLoading] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Profile Form State
  const [profile, setProfile] = useState({
    age: 26,
    heightCm: 175,
    weightKg: 74,
    fitnessGoal: 'Muscle Gain & Strength',
    experienceLevel: 'Beginner',
    availableDays: ['Monday', 'Wednesday', 'Friday'],
    sessionDuration: 45,
    healthConditions: [],
    declaredInjuries: '',
    selectedGym: 'Downtown Metro Fitness',
  });

  // Active Plan & Workflow State
  const [currentPlan, setCurrentPlan] = useState(null);
  const [workflowState, setWorkflowState] = useState(null);
  const [workflowHistory, setWorkflowHistory] = useState([]);
  const [pendingApprovals, setPendingApprovals] = useState([]);

  // Progress Form State
  const [progressForm, setProgressForm] = useState({
    weekNumber: 1,
    completedSessions: 3,
    weightKg: 73.8,
    rpeRating: 7, // 1-10
    performanceNotes: 'Completed all sets with good form. Squats felt slightly easier on Friday.',
  });

  const isTrainerOrAdmin = user?.role === 'Trainer' || user?.role === 'Admin' || user?.role === 1 || user?.role === 2;

  useEffect(() => {
    loadInitialData();
  }, [isLoggedIn]);

  async function loadInitialData() {
    setLoading(true);
    try {
      const [savedProfile, activePlan, history, approvals] = await Promise.all([
        getFitnessProfile().catch(() => null),
        getCurrentWorkoutPlan().catch(() => null),
        getWorkflowHistory().catch(() => []),
        isTrainerOrAdmin ? getPendingApprovals().catch(() => []) : Promise.resolve([])
      ]);

      if (savedProfile) setProfile(prev => ({ ...prev, ...savedProfile }));
      if (activePlan) setCurrentPlan(activePlan);
      if (history) setWorkflowHistory(history);
      if (approvals) setPendingApprovals(approvals);
    } catch (err) {
      console.warn('Data load warning:', err);
    } finally {
      setLoading(false);
    }
  }

  const toggleDay = (day) => {
    setProfile(prev => {
      const exists = prev.availableDays.includes(day);
      const updated = exists ? prev.availableDays.filter(d => d !== day) : [...prev.availableDays, day];
      return { ...prev, availableDays: updated };
    });
  };

  const handleHealthToggle = (condition) => {
    setProfile(prev => {
      const exists = prev.healthConditions.includes(condition);
      const updated = exists ? prev.healthConditions.filter(c => c !== condition) : [...prev.healthConditions, condition];
      return { ...prev, healthConditions: updated };
    });
  };

  const handleGeneratePlan = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    setFeedbackMsg(null);
    setWorkflowState({ step: 'Screening', status: 'RUNNING' });

    try {
      await saveFitnessProfile(profile);
      
      const payload = {
        age: Number(profile.age),
        heightCm: Number(profile.heightCm),
        weightKg: Number(profile.weightKg),
        fitnessGoal: profile.fitnessGoal,
        experienceLevel: profile.experienceLevel,
        availableDays: profile.availableDays,
        sessionDuration: Number(profile.sessionDuration),
        selectedGym: profile.selectedGym,
        healthInformation: {
          conditions: profile.healthConditions,
          injuries: profile.declaredInjuries
        }
      };

      const result = await startFitnessWorkflow(payload);

      if (!result.success) {
        setWorkflowState({ step: 'Safe Failure', status: 'FAILED' });
        setErrorMsg(result.error?.message || 'Workflow halted due to health screening policy.');
      } else {
        setWorkflowState({ step: 'Awaiting Approval', status: 'PENDING' });
        setFeedbackMsg(result.message || 'Adaptive plan created and queued for human approval!');
        if (result.plan) {
          setCurrentPlan(result.plan);
        }
        setActiveTab('plan');
      }
      loadInitialData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to initiate agent workflow.');
    } finally {
      setLoading(false);
    }
  };

  const handleProgressSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    try {
      await logWorkoutProgress(progressForm);
      setFeedbackMsg('Weekly progress recorded successfully!');
      loadInitialData();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save progress.');
    } finally {
      setLoading(false);
    }
  };

  const handleNextSchedule = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await generateNextSchedule(currentPlan?.workflow_id || 'current');
      if (res.success && res.plan) {
        setCurrentPlan(res.plan);
        setFeedbackMsg(res.message || 'Next week schedule generated with adaptive progression!');
        setActiveTab('plan');
      } else {
        setErrorMsg(res.error?.message || 'Could not generate next schedule.');
      }
      loadInitialData();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprovalAction = async (workflowId, decision) => {
    setLoading(true);
    try {
      await reviewWorkflowPlan(workflowId, { decision, reason: `Approved by Trainer/Admin` });
      setFeedbackMsg(`Plan decision '${decision}' applied.`);
      loadInitialData();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="fitness-page">
      <div className="container">
        {/* Hero Section */}
        <section className="fitness-hero">
          <div className="fitness-hero-header">
            <div>
              <p className="section-label">Agentic Fitness System</p>
              <h1 className="section-title">AI Self-Scheduling & Adaptive Workout</h1>
            </div>
            <div className="fitness-hero-badges">
              <span className="badge badge-ai">⚡ LangGraph Orchestrator</span>
              <span className="badge badge-ai">🛡️ RUG Governed</span>
              <span className={`badge badge-status ${currentPlan ? 'active' : 'pending'}`}>
                {currentPlan ? `Plan: Week ${currentPlan.week || 1} (${currentPlan.status || 'Active'})` : 'No Active Plan'}
              </span>
            </div>
          </div>

          {/* Stepper */}
          <div className="workflow-stepper">
            <div className={`step-item ${workflowState ? 'completed' : 'active'}`}>
              <div className="step-circle">1</div>
              <span className="step-label">Intake & Screening</span>
            </div>
            <div className={`step-item ${workflowState?.step === 'Planning' || workflowState?.step === 'Validation' || workflowState?.status === 'PENDING' ? 'completed' : ''}`}>
              <div className="step-circle">2</div>
              <span className="step-label">AI Planning & Tools</span>
            </div>
            <div className={`step-item ${workflowState?.status === 'PENDING' || currentPlan?.status === 'APPROVED' ? 'completed' : ''}`}>
              <div className="step-circle">3</div>
              <span className="step-label">Deterministic Validation</span>
            </div>
            <div className={`step-item ${currentPlan?.status === 'APPROVED' ? 'completed' : (workflowState?.status === 'PENDING' ? 'active' : '')}`}>
              <div className="step-circle">4</div>
              <span className="step-label">Human Approval</span>
            </div>
            <div className={`step-item ${currentPlan?.status === 'APPROVED' ? 'active' : ''}`}>
              <div className="step-circle">5</div>
              <span className="step-label">Adaptive Progression</span>
            </div>
          </div>
        </section>

        {/* Global Feedback Banners */}
        {errorMsg && (
          <div className="alert-box alert-danger">
            <span>⚠️</span>
            <div>
              <strong>Action Blocked:</strong> {errorMsg}
            </div>
          </div>
        )}
        {feedbackMsg && (
          <div className="alert-box alert-success">
            <span>✅</span>
            <div>{feedbackMsg}</div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="fitness-tabs">
          <button className={`tab-btn ${activeTab === 'plan' ? 'active' : ''}`} onClick={() => setActiveTab('plan')}>
            📋 Current Schedule
          </button>
          <button className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => setActiveTab('profile')}>
            🎯 Fitness Intake & Profile
          </button>
          <button className={`tab-btn ${activeTab === 'progress' ? 'active' : ''}`} onClick={() => setActiveTab('progress')}>
            📊 Log Progress & Next Week
          </button>
          <button className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
            📜 Workflow & Audit Logs
          </button>
          {isTrainerOrAdmin && (
            <button className={`tab-btn ${activeTab === 'approvals' ? 'active' : ''}`} onClick={() => setActiveTab('approvals')}>
              🛡️ Trainer Approvals {pendingApprovals.length > 0 && `(${pendingApprovals.length})`}
            </button>
          )}
        </div>

        {/* TAB 1: Current Schedule */}
        {activeTab === 'plan' && (
          <div>
            {!currentPlan ? (
              <div className="fitness-card text-center" style={{ textAlign: 'center', padding: '60px 20px' }}>
                <h3 className="card-title" style={{ justifyContent: 'center' }}>No Workout Schedule Generated Yet</h3>
                <p style={{ color: 'var(--text-secondary)', margin: '14px 0 24px' }}>
                  Complete your fitness intake screening to generate your personalized, conservative beginner workout plan.
                </p>
                <button className="btn-primary" onClick={() => setActiveTab('profile')}>
                  Start Fitness Intake
                </button>
              </div>
            ) : (
              <div className="fitness-card">
                <div className="card-header">
                  <div>
                    <h2 className="card-title">
                      {currentPlan.title || `Week ${currentPlan.week} Adaptive Schedule`}
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      Experience: <strong>{currentPlan.target_experience || 'Beginner'}</strong> • Target Session: <strong>{currentPlan.session_duration_minutes || 45} mins</strong>
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <span className={`badge badge-status ${currentPlan.status === 'APPROVED' ? 'active' : 'pending'}`}>
                      Status: {currentPlan.status || 'Active'}
                    </span>
                    <button className="btn-secondary" style={{ padding: '8px 16px', fontSize: '0.85rem' }} onClick={() => setActiveTab('progress')}>
                      Log Session Progress
                    </button>
                  </div>
                </div>

                <div className="workout-days-container">
                  {(currentPlan.days || []).map((day, dIdx) => (
                    <div key={dIdx} className="day-card">
                      <div className="day-card-header">
                        <div>
                          <h3 className="day-name">{day.day}</h3>
                          <p className="day-focus">{day.focus}</p>
                        </div>
                        <span className="stat-pill">{day.duration_minutes || 45} mins</span>
                      </div>

                      <div className="exercise-list">
                        {(day.exercises || []).map((ex, eIdx) => (
                          <div key={eIdx} className="exercise-item">
                            <div className="exercise-title-row">
                              <span className="exercise-name">{eIdx + 1}. {ex.name}</span>
                              <div className="exercise-stats">
                                <span className="stat-pill">{ex.sets} Sets</span>
                                <span className="stat-pill">{ex.reps} Reps</span>
                                <span className="stat-pill">Rest: {ex.rest}</span>
                                <span className="stat-pill">Equip: {ex.equipment}</span>
                              </div>
                            </div>
                            <p className="exercise-notes">{ex.instructions}</p>
                            {ex.safety_notes && (
                              <span className="exercise-safety">🛡️ Safety Note: {ex.safety_notes}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Fitness Profile & Intake */}
        {activeTab === 'profile' && (
          <form onSubmit={handleGeneratePlan} className="fitness-grid">
            <div className="fitness-card">
              <div className="card-header">
                <h2 className="card-title">1. Personal Profile & Objectives</h2>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Age</label>
                  <input
                    type="number"
                    min="16"
                    max="90"
                    className="form-input"
                    value={profile.age}
                    onChange={e => setProfile({ ...profile, age: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Experience Level</label>
                  <select
                    className="form-select"
                    value={profile.experienceLevel}
                    onChange={e => setProfile({ ...profile, experienceLevel: e.target.value })}
                  >
                    <option value="Beginner">Beginner (First time / Returning)</option>
                    <option value="Intermediate">Intermediate (1-2 years)</option>
                    <option value="Advanced">Advanced (3+ years)</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Height (cm)</label>
                  <input
                    type="number"
                    min="100"
                    max="250"
                    className="form-input"
                    value={profile.heightCm}
                    onChange={e => setProfile({ ...profile, heightCm: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Weight (kg)</label>
                  <input
                    type="number"
                    min="30"
                    max="250"
                    className="form-input"
                    value={profile.weightKg}
                    onChange={e => setProfile({ ...profile, weightKg: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Primary Fitness Goal</label>
                <select
                  className="form-select"
                  value={profile.fitnessGoal}
                  onChange={e => setProfile({ ...profile, fitnessGoal: e.target.value })}
                >
                  <option value="Muscle Gain & Strength">Muscle Gain & Strength</option>
                  <option value="Fat Loss & Conditioning">Fat Loss & Conditioning</option>
                  <option value="General Health & Posture">General Health & Posture</option>
                  <option value="Athletic Endurance">Athletic Endurance</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Preferred Session Duration</label>
                <select
                  className="form-select"
                  value={profile.sessionDuration}
                  onChange={e => setProfile({ ...profile, sessionDuration: e.target.value })}
                >
                  <option value="30">30 minutes (Express)</option>
                  <option value="45">45 minutes (Standard Beginner)</option>
                  <option value="60">60 minutes (Comprehensive)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Available Workout Days</label>
                <div className="days-picker">
                  {DAYS_OF_WEEK.map(d => (
                    <button
                      type="button"
                      key={d}
                      className={`day-chip ${profile.availableDays.includes(d) ? 'selected' : ''}`}
                      onClick={() => toggleDay(d)}
                    >
                      {d.substring(0, 3)}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="fitness-card">
              <div className="card-header">
                <h2 className="card-title">2. Conservative Health Screening</h2>
              </div>

              <div className="alert-box alert-info">
                <span>🛡️</span>
                <div>
                  <strong>Health Guardrail:</strong> Automated workout generation performs conservative safety screening. Serious declared symptoms require clearance from a qualified professional.
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Declared Health Conditions (Select any that apply)</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    'Chest pain during exertion / Heart condition',
                    'Severe respiratory issue / Uncontrolled asthma',
                    'Chronic lower back pain / Herniation',
                    'Joint hypermobility / Recent knee surgery',
                    'None / Cleared for physical exercise',
                  ].map((cond, i) => (
                    <label key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={profile.healthConditions.includes(cond)}
                        onChange={() => handleHealthToggle(cond)}
                      />
                      <span>{cond}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Declared Physical Limitations / Injuries</label>
                <textarea
                  className="form-textarea"
                  rows="3"
                  placeholder="e.g. Mild right shoulder impingement when pressing overhead..."
                  value={profile.declaredInjuries}
                  onChange={e => setProfile({ ...profile, declaredInjuries: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Selected Gym / Equipment Facility</label>
                <input
                  type="text"
                  className="form-input"
                  value={profile.selectedGym}
                  onChange={e => setProfile({ ...profile, selectedGym: e.target.value })}
                  placeholder="e.g. Downtown Metro Fitness"
                />
              </div>

              <button type="submit" className="btn-primary" style={{ width: '100%', marginTop: '16px' }} disabled={loading}>
                {loading ? 'Executing Multi-Agent Workflow...' : '⚡ Generate My Fitness Plan'}
              </button>
            </div>
          </form>
        )}

        {/* TAB 3: Progress Tracking & Next Schedule */}
        {activeTab === 'progress' && (
          <div className="fitness-grid">
            <div className="fitness-card">
              <div className="card-header">
                <h2 className="card-title">Log Weekly Performance</h2>
              </div>

              <form onSubmit={handleProgressSubmit}>
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Week Number</label>
                    <input
                      type="number"
                      min="1"
                      className="form-input"
                      value={progressForm.weekNumber}
                      onChange={e => setProgressForm({ ...progressForm, weekNumber: Number(e.target.value) })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Sessions Completed</label>
                    <input
                      type="number"
                      min="0"
                      max="7"
                      className="form-input"
                      value={progressForm.completedSessions}
                      onChange={e => setProgressForm({ ...progressForm, completedSessions: Number(e.target.value) })}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">Current Weight (kg)</label>
                    <input
                      type="number"
                      step="0.1"
                      className="form-input"
                      value={progressForm.weightKg}
                      onChange={e => setProgressForm({ ...progressForm, weightKg: Number(e.target.value) })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Rate of Perceived Exertion (RPE 1-10)</label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      className="form-input"
                      value={progressForm.rpeRating}
                      onChange={e => setProgressForm({ ...progressForm, rpeRating: Number(e.target.value) })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Performance Notes & Feedback</label>
                  <textarea
                    className="form-textarea"
                    rows="3"
                    value={progressForm.performanceNotes}
                    onChange={e => setProgressForm({ ...progressForm, performanceNotes: e.target.value })}
                  />
                </div>

                <button type="submit" className="btn-primary" style={{ width: '100%' }} disabled={loading}>
                  Save Weekly Progress
                </button>
              </form>
            </div>

            <div className="fitness-card">
              <div className="card-header">
                <h2 className="card-title">Adaptive Progression Agent</h2>
              </div>
              <div className="alert-box alert-info">
                <span>📈</span>
                <div>
                  <strong>Progress Analysis:</strong> The agent analyzes completed sessions, adherence rate, and RPE to generate your next week's schedule with conservative progressive overload.
                </div>
              </div>

              <div style={{ margin: '24px 0' }}>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  Current Adherence: <strong>100% (3/3 sessions completed)</strong>
                </p>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  Recommended Adaptation: <strong>Gradual volume increase (+1 set on primary compounds)</strong>
                </p>
              </div>

              <button className="btn-primary" style={{ width: '100%' }} onClick={handleNextSchedule} disabled={loading}>
                {loading ? 'Analyzing Progress...' : '🚀 Generate Next Schedule'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 4: Workflow Audit Logs */}
        {activeTab === 'history' && (
          <div className="fitness-card">
            <div className="card-header">
              <h2 className="card-title">Auditable Execution History & Tool Invocations</h2>
            </div>
            {workflowHistory.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No workflow executions recorded yet.</p>
            ) : (
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>Workflow ID</th>
                    <th>Timestamp</th>
                    <th>Status</th>
                    <th>Tool Calls & Validation</th>
                  </tr>
                </thead>
                <tbody>
                  {workflowHistory.map((h, idx) => (
                    <tr key={idx}>
                      <td style={{ fontFamily: 'monospace', color: 'var(--accent)' }}>{h.workflow_id}</td>
                      <td>{new Date(h.timestamp).toLocaleString()}</td>
                      <td>
                        <span className={`badge badge-status ${h.status === 'APPROVED' ? 'active' : 'pending'}`}>
                          {h.status}
                        </span>
                      </td>
                      <td>
                        {(h.tool_calls || []).map((t, tidx) => (
                          <div key={tidx} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            • {t.tool}: <strong>{t.status}</strong>
                          </div>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* TAB 5: Trainer / Admin Approvals */}
        {activeTab === 'approvals' && isTrainerOrAdmin && (
          <div className="fitness-card">
            <div className="card-header">
              <h2 className="card-title">Pending Human Approvals</h2>
            </div>
            {pendingApprovals.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No pending plans requiring review.</p>
            ) : (
              pendingApprovals.map((plan, pidx) => (
                <div key={pidx} className="approval-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <h3 style={{ color: 'var(--accent)' }}>{plan.title} (Workflow: {plan.workflow_id})</h3>
                    <span className="badge badge-status pending">Needs Approval</span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
                    User Level: {plan.target_experience} • Duration: {plan.session_duration_minutes} mins • Days: {plan.days?.length}
                  </p>

                  <div className="approval-actions">
                    <button className="btn-approve" onClick={() => handleApprovalAction(plan.workflow_id, 'APPROVE')}>
                      ✓ Approve Plan
                    </button>
                    <button className="btn-revision" onClick={() => handleApprovalAction(plan.workflow_id, 'REQUEST_REVISION')}>
                      ↻ Request Revision
                    </button>
                    <button className="btn-reject" onClick={() => handleApprovalAction(plan.workflow_id, 'REJECT')}>
                      ✗ Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </main>
  );
}
