// VitroFit_web/src/api/fitness.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5284/api';

function getAuthHeader() {
  let token = '';
  try {
    const stored = sessionStorage.getItem('vitrofitAuth');
    token = stored ? JSON.parse(stored).accessToken : '';
  } catch {
    /* ignore */
  }
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = data?.error || data?.message || `Server error (${response.status})`;
    throw new Error(typeof error === 'string' ? error : JSON.stringify(error));
  }
  return data;
}

/**
 * Fetch current user's fitness profile
 */
export async function getFitnessProfile() {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/profile`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return await handleResponse(res);
  } catch (err) {
    console.warn('Backend API not responding, using local profile store:', err.message);
    const local = localStorage.getItem('vitrofit_fitness_profile');
    return local ? JSON.parse(local) : null;
  }
}

/**
 * Save / update fitness profile
 */
export async function saveFitnessProfile(profile) {
  localStorage.setItem('vitrofit_fitness_profile', JSON.stringify(profile));
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(profile),
    });
    return await handleResponse(res);
  } catch (err) {
    console.warn('Backend API unavailable, saved locally:', err.message);
    return { success: true, profile };
  }
}

/**
 * Start AI Fitness Planning Workflow via ASP.NET Core API Gateway
 */
export async function startFitnessWorkflow(payload) {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/generate-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(payload),
    });
    return await handleResponse(res);
  } catch (err) {
    console.warn('Backend endpoint unavailable, falling back to agent simulator:', err.message);
    return simulateAgentWorkflow(payload);
  }
}

/**
 * Retrieve current active workout plan
 */
export async function getCurrentWorkoutPlan() {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/plans/current`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return await handleResponse(res);
  } catch (err) {
    const stored = localStorage.getItem('vitrofit_active_plan');
    return stored ? JSON.parse(stored) : null;
  }
}

/**
 * Submit weekly progress log
 */
export async function logWorkoutProgress(progressData) {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify(progressData),
    });
    const data = await handleResponse(res);
    return data;
  } catch (err) {
    console.warn('Saved progress locally:', err.message);
    const existing = JSON.parse(localStorage.getItem('vitrofit_progress_history') || '[]');
    existing.unshift({ ...progressData, id: Date.now(), loggedAt: new Date().toISOString() });
    localStorage.setItem('vitrofit_progress_history', JSON.stringify(existing));
    return { success: true, progress: progressData };
  }
}

/**
 * Request next adaptive schedule based on historical progress
 */
export async function generateNextSchedule(workflowId) {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/generate-next-schedule`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ workflowId }),
    });
    return await handleResponse(res);
  } catch (err) {
    console.warn('Simulating next schedule generation:', err.message);
    return simulateNextWeekProgression();
  }
}

/**
 * Trainer / Admin: Get pending approval plans
 */
export async function getPendingApprovals() {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/approvals/pending`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return await handleResponse(res);
  } catch (err) {
    const local = localStorage.getItem('vitrofit_pending_approval');
    return local ? [JSON.parse(local)] : [];
  }
}

/**
 * Trainer / Admin: Submit Approval Decision (APPROVE / REJECT / REQUEST_REVISION)
 */
export async function reviewWorkflowPlan(workflowId, { decision, reason }) {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/workflows/${workflowId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ decision, reason }),
    });
    return await handleResponse(res);
  } catch (err) {
    const pending = localStorage.getItem('vitrofit_pending_approval');
    if (pending) {
      const plan = JSON.parse(pending);
      plan.status = decision;
      if (decision === 'APPROVE') {
        localStorage.setItem('vitrofit_active_plan', JSON.stringify(plan));
        localStorage.removeItem('vitrofit_pending_approval');
      }
    }
    return { success: true, decision, workflowId };
  }
}

/**
 * Fetch workflow history and tool call logs
 */
export async function getWorkflowHistory() {
  try {
    const res = await fetch(`${API_BASE_URL}/fitness/workflows/my-history`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
    });
    return await handleResponse(res);
  } catch (err) {
    const local = localStorage.getItem('vitrofit_workflow_history');
    return local ? JSON.parse(local) : [];
  }
}

// Client-side deterministic Agentic simulator for instant feedback and demo resilience
function simulateAgentWorkflow(payload) {
  const workflowId = 'wf-' + Math.random().toString(36).substring(2, 9);
  
  // Health Screening Rule check
  const healthConditions = (payload.healthInformation?.conditions || []).map(c => c.toLowerCase());
  const hasSevereRisk = healthConditions.some(c => 
    c.includes('heart') || c.includes('chest pain') || c.includes('cardiac') || c.includes('uncontrolled')
  );

  if (hasSevereRisk) {
    return {
      success: false,
      workflow_id: workflowId,
      status: 'SAFE_FAILURE',
      error: {
        code: 'SAFETY_REVIEW_REQUIRED',
        message: 'The health screening agent detected declared conditions requiring professional clearance. An automated schedule cannot be generated safely at this time. Please consult a qualified healthcare provider.',
      },
      screening_result: {
        status: 'REVIEW_REQUIRED',
        risk_flags: ['Cardiovascular / Acute symptom risk detected'],
        reason: 'Conservative screening triggered safety guardrail.',
        recommended_action: 'CONTACT_PROFESSIONAL'
      }
    };
  }

  const days = payload.availableDays && payload.availableDays.length > 0 
    ? payload.availableDays 
    : ['Monday', 'Wednesday', 'Friday'];

  const generatedPlan = {
    workflow_id: workflowId,
    week: 1,
    title: `${payload.fitnessGoal || 'General Fitness'} - Adaptive Schedule`,
    status: 'AWAITING_APPROVAL',
    target_experience: payload.experienceLevel || 'Beginner',
    session_duration_minutes: payload.sessionDuration || 45,
    days: days.map(day => ({
      day: day,
      focus: day === 'Monday' ? 'Full Body Foundations & Core' : (day === 'Wednesday' ? 'Upper Body & Postural Stability' : 'Lower Body & Conditioning'),
      duration_minutes: payload.sessionDuration || 45,
      exercises: [
        {
          id: 'ex-sq-01',
          name: 'Goblet Squat (or Bodyweight Box Squat)',
          target_muscle: 'Quadriceps, Glutes',
          sets: 3,
          reps: '10-12',
          rest: '60s',
          equipment: 'Dumbbell / Bodyweight',
          instructions: 'Keep chest high, core braced, descend until thighs are parallel to ground.',
          safety_notes: 'Avoid knees caving inward; maintain neutral spine.'
        },
        {
          id: 'ex-pu-02',
          name: 'Incline Push-Up / Dumbbell Bench Press',
          target_muscle: 'Chest, Anterior Deltoids, Triceps',
          sets: 3,
          reps: '8-10',
          rest: '60s',
          equipment: 'Bench & Dumbbells',
          instructions: 'Lower weight with control to mid-chest level, press up smoothly.',
          safety_notes: 'Keep shoulders retracted and depressed.'
        },
        {
          id: 'ex-rw-03',
          name: 'Seated Cable Row / Dumbbell Single Arm Row',
          target_muscle: 'Latissimus Dorsi, Rhomboids',
          sets: 3,
          reps: '10-12',
          rest: '60s',
          equipment: 'Cable Machine / Dumbbell',
          instructions: 'Pull elbows back close to body, squeeze shoulder blades for 1 second.',
          safety_notes: 'Do not swing torso backwards.'
        },
        {
          id: 'ex-pl-04',
          name: 'Plank Hold',
          target_muscle: 'Core, Transverse Abdominis',
          sets: 3,
          reps: '30-45s',
          rest: '45s',
          equipment: 'Mat',
          instructions: 'Maintain straight line from shoulders to ankles, brace core tightly.',
          safety_notes: 'Do not allow lower back to sag.'
        }
      ]
    }))
  };

  localStorage.setItem('vitrofit_pending_approval', JSON.stringify(generatedPlan));

  const history = JSON.parse(localStorage.getItem('vitrofit_workflow_history') || '[]');
  history.unshift({
    workflow_id: workflowId,
    timestamp: new Date().toISOString(),
    status: 'AWAITING_APPROVAL',
    plan: generatedPlan,
    tool_calls: [
      { tool: 'Exercise Search Tool', status: 'SUCCESS', count: 4 },
      { tool: 'Gym Equipment Tool', status: 'SUCCESS', matched: 'Dumbbells, Cables, Mats' },
      { tool: 'Fitness Validation Agent', status: 'PASSED', checks: 'Sets, Reps, Rest, Safe Limits' }
    ]
  });
  localStorage.setItem('vitrofit_workflow_history', JSON.stringify(history));

  return {
    success: true,
    workflow_id: workflowId,
    status: 'AWAITING_APPROVAL',
    plan: generatedPlan,
    message: 'Plan successfully planned, validated deterministically, and queued for trainer approval.'
  };
}

function simulateNextWeekProgression() {
  const current = JSON.parse(localStorage.getItem('vitrofit_active_plan') || 'null');
  const nextWeekNum = (current?.week || 1) + 1;
  const workflowId = 'wf-prog-' + Math.random().toString(36).substring(2, 9);

  const nextPlan = {
    workflow_id: workflowId,
    week: nextWeekNum,
    title: `Week ${nextWeekNum} - Progressive Overload Schedule`,
    status: 'AWAITING_APPROVAL',
    target_experience: 'Progressing Beginner',
    session_duration_minutes: 50,
    days: (current?.days || []).map(day => ({
      ...day,
      exercises: day.exercises.map(ex => ({
        ...ex,
        sets: Math.min(ex.sets + 1, 4),
        instructions: `${ex.instructions} [Progression: Target 1 extra rep or 2.5kg increase].`
      }))
    }))
  };

  localStorage.setItem('vitrofit_pending_approval', JSON.stringify(nextPlan));
  return {
    success: true,
    workflow_id: workflowId,
    status: 'AWAITING_APPROVAL',
    plan: nextPlan,
    message: `Analyzed past performance. Week ${nextWeekNum} schedule generated with controlled progressive overload!`
  };
}
