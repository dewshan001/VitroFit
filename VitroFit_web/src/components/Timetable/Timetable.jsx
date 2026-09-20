import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { getTimetable, createSlot, updateSlot, deleteSlot } from '../../api/timetable';
import { getWorkouts } from '../../api/workouts';
import './Timetable.css';

// Matches .NET's System.DayOfWeek enum values (Sunday = 0 .. Saturday = 6)
const days = [
  { value: 1, label: 'Monday' },
  { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' },
  { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' },
  { value: 6, label: 'Saturday' },
  { value: 0, label: 'Sunday' },
];

const hourRows = Array.from({ length: 16 }, (_, i) => 6 + i); // 6 AM - 9 PM

function formatHour(hour) {
  const h = hour % 24;
  const period = h >= 12 ? 'PM' : 'AM';
  const displayHour = h % 12 === 0 ? 12 : h % 12;
  return `${displayHour}:00 ${period}`;
}

// "06:00:00" -> "06:00"
function toInputTime(timeStr) {
  return timeStr ? timeStr.slice(0, 5) : '';
}

// "06:00" -> "06:00:00"
function toApiTime(timeStr) {
  return timeStr && timeStr.length === 5 ? `${timeStr}:00` : timeStr;
}

function timeToHourFraction(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  return h + m / 60;
}

function emptyForm(workouts) {
  return {
    day: 1,
    startTime: '06:00',
    endTime: '07:00',
    title: '',
    workoutId: workouts[0]?.id ?? '',
  };
}

export default function Timetable() {
  const { isLoggedIn } = useAuth();
  const [slots, setSlots] = useState([]);
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(emptyForm([]));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!isLoggedIn) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    Promise.all([getTimetable(), getWorkouts()])
      .then(([slotsData, workoutsData]) => {
        if (cancelled) return;
        setSlots(slotsData);
        setWorkouts(workoutsData);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isLoggedIn]);

  function openAddForm(day) {
    setEditingId(null);
    setForm({ ...emptyForm(workouts), day: day ?? 1 });
    setShowForm(true);
    setError('');
  }

  function openEditForm(slot) {
    setEditingId(slot.id);
    setForm({
      day: slot.day,
      startTime: toInputTime(slot.startTime),
      endTime: toInputTime(slot.endTime),
      title: slot.title,
      workoutId: slot.workoutId,
    });
    setShowForm(true);
    setError('');
  }

  function handleWorkoutChange(workoutId) {
    const workout = workouts.find((w) => w.id === workoutId);
    setForm((prev) => ({
      ...prev,
      workoutId,
      // Auto-fill the title when it's empty or still matches the previously selected workout's name
      title: !prev.title || workouts.some((w) => w.name === prev.title)
        ? (workout?.name ?? prev.title)
        : prev.title,
    }));
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm(workouts));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.workoutId) {
      setError('Please select a workout.');
      return;
    }
    if (!form.title.trim()) {
      setError('Please enter a title for this slot.');
      return;
    }
    if (form.endTime <= form.startTime) {
      setError('End time must be after start time.');
      return;
    }

    const payload = {
      day: Number(form.day),
      startTime: toApiTime(form.startTime),
      endTime: toApiTime(form.endTime),
      title: form.title.trim(),
      workoutId: Number(form.workoutId),
    };

    setSaving(true);
    setError('');
    try {
      if (editingId) {
        const updated = await updateSlot(editingId, payload);
        setSlots((prev) => prev.map((s) => (s.id === editingId ? updated : s)));
      } else {
        const created = await createSlot(payload);
        setSlots((prev) => [...prev, created]);
      }
      closeForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    setSaving(true);
    setError('');
    try {
      await deleteSlot(id);
      setSlots((prev) => prev.filter((s) => s.id !== id));
      if (editingId === id) closeForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="tt-page">
        <section className="tt-hero">
          <div className="tt-hero-overlay"></div>
          <div className="container tt-hero-content">
            <div className="tt-breadcrumb">
              Home &gt; <span>My Timetable</span>
            </div>
            <h1 className="tt-hero-title">
              PLAN YOUR <span className="outline-text">WEEKLY</span><br />
              <span className="outline-text">WORKOUT</span> SCHEDULE
            </h1>
          </div>
        </section>
        <section className="tt-section container">
          <p className="tt-login-prompt">Please log in to build and manage your personal timetable.</p>
        </section>
      </div>
    );
  }

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
          <div className="tt-breadcrumb">
            Home &gt; <span>My Timetable</span>
          </div>
          <h1 className="tt-hero-title">
            YOUR WEEKLY <span className="outline-text">WORKOUT</span><br />
            <span className="outline-text">SCHEDULE</span> AT A GLANCE
          </h1>
        </div>
      </section>

      {/* Timetable Section */}
      <section className="tt-section container" id="timetable">
        <div className="tt-toolbar">
          <button className="btn-primary" onClick={() => openAddForm()} disabled={loading}>+ Add Slot</button>
        </div>

        {error && <p className="tt-error">{error}</p>}

        {loading ? (
          <p className="tt-loading">Loading your timetable...</p>
        ) : slots.length === 0 ? (
          <p className="tt-empty">No workouts scheduled yet — add your first slot.</p>
        ) : (
          <div className="tt-grid-wrapper">
            <div className="tt-grid">
              <div className="tt-header-cell"></div>
              {days.map((d) => (
                <div key={d.value} className="tt-header-cell">{d.label}</div>
              ))}

              {hourRows.map((hour) => (
                <div style={{ display: 'contents' }} key={hour}>
                  <div className="tt-time-cell">{formatHour(hour)}</div>
                  {days.map((d) => {
                    const slot = slots.find(
                      (s) => s.day === d.value && Math.floor(timeToHourFraction(toInputTime(s.startTime))) === hour
                    );
                    return (
                      <div
                        key={`${d.value}-${hour}`}
                        className="tt-cell"
                        onClick={() => !slot && openAddForm(d.value)}
                      >
                        {slot && (
                          <div className="tt-event" onClick={(e) => { e.stopPropagation(); openEditForm(slot); }}>
                            <div className="tt-event-title">{slot.title}</div>
                            <div className="tt-event-time">
                              {toInputTime(slot.startTime)} - {toInputTime(slot.endTime)}
                            </div>
                            {slot.workoutCategory && (
                              <div className="tt-event-category">{slot.workoutCategory}</div>
                            )}
                            <button
                              className="tt-event-delete"
                              onClick={(e) => { e.stopPropagation(); handleDelete(slot.id); }}
                              disabled={saving}
                            >
                              Remove
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {showForm && (
        <div className="tt-modal-overlay" onClick={closeForm}>
          <form className="tt-modal" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
            <h3>{editingId ? 'Edit Slot' : 'Add Slot'}</h3>

            <label>
              Day
              <select value={form.day} onChange={(e) => setForm({ ...form, day: Number(e.target.value) })}>
                {days.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </label>

            <label>
              Workout
              <select
                value={form.workoutId}
                onChange={(e) => handleWorkoutChange(Number(e.target.value))}
                required
              >
                <option value="" disabled>Select a workout</option>
                {workouts.map((w) => (
                  <option key={w.id} value={w.id}>{w.name} ({w.category})</option>
                ))}
              </select>
            </label>

            <label>
              Start Time
              <input
                type="time"
                value={form.startTime}
                onChange={(e) => setForm({ ...form, startTime: e.target.value })}
                required
              />
            </label>

            <label>
              End Time
              <input
                type="time"
                value={form.endTime}
                onChange={(e) => setForm({ ...form, endTime: e.target.value })}
                required
              />
            </label>

            <label>
              Title
              <input
                type="text"
                placeholder="e.g. Leg Day"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
                maxLength={100}
              />
            </label>

            {error && <p className="tt-error">{error}</p>}

            <div className="tt-modal-actions">
              <button type="button" onClick={closeForm} disabled={saving}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
              {editingId && (
                <button
                  type="button"
                  className="tt-modal-delete"
                  onClick={() => handleDelete(editingId)}
                  disabled={saving}
                >
                  Delete
                </button>
              )}
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
