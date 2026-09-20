import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUsersByRole, createUser, deleteUser, getWorkouts, createWorkout, updateWorkout, deleteWorkout } from '../api/admin';
import './AdminDashboardPage.css';

const ROLES = {
  USER: 0,
  TRAINER: 1,
  ADMIN: 2,
  GYM_OWNER: 3
};

const TABS = [
  { id: 'users', label: 'Members', role: ROLES.USER },
  { id: 'trainers', label: 'Trainers', role: ROLES.TRAINER },
  { id: 'gym-owners', label: 'Gym Owners', role: ROLES.GYM_OWNER },
  { id: 'workouts', label: 'Workouts', role: null }
];

const emptyWorkoutForm = { name: '', category: '', description: '' };

export default function AdminDashboardPage() {
  const [activeTab, setActiveTab] = useState(TABS[0]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Create Form State
  const [createForm, setCreateForm] = useState({
    firstName: '', lastName: '', email: '', phone: '', password: ''
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');

  // Workouts tab state
  const [workouts, setWorkouts] = useState([]);
  const [isWorkoutFormOpen, setIsWorkoutFormOpen] = useState(false);
  const [editingWorkout, setEditingWorkout] = useState(null);
  const [workoutForm, setWorkoutForm] = useState(emptyWorkoutForm);
  const [workoutSaving, setWorkoutSaving] = useState(false);
  const [workoutFormError, setWorkoutFormError] = useState('');
  const [isWorkoutDeleteModalOpen, setIsWorkoutDeleteModalOpen] = useState(false);
  const [selectedWorkout, setSelectedWorkout] = useState(null);
  const [workoutDeleteError, setWorkoutDeleteError] = useState('');

  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is admin
    const stored = sessionStorage.getItem('vitrofitAuth');
    if (stored) {
      const { user } = JSON.parse(stored);
      if (user.role !== ROLES.ADMIN && user.role !== 'Admin') {
        navigate('/'); // Redirect non-admins
        return;
      }
    } else {
      navigate('/login');
      return;
    }

    if (activeTab.id === 'workouts') {
      fetchWorkouts();
    } else {
      fetchUsers();
    }
  }, [activeTab]);

  const fetchWorkouts = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getWorkouts();
      setWorkouts(data || []);
    } catch (err) {
      setError('Failed to fetch workouts: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const openCreateWorkoutForm = () => {
    setEditingWorkout(null);
    setWorkoutForm(emptyWorkoutForm);
    setWorkoutFormError('');
    setIsWorkoutFormOpen(true);
  };

  const openEditWorkoutForm = (workout) => {
    setEditingWorkout(workout);
    setWorkoutForm({ name: workout.name, category: workout.category, description: workout.description || '' });
    setWorkoutFormError('');
    setIsWorkoutFormOpen(true);
  };

  const handleWorkoutFormSubmit = async (e) => {
    e.preventDefault();
    setWorkoutSaving(true);
    setWorkoutFormError('');

    try {
      if (editingWorkout) {
        await updateWorkout(editingWorkout.id, workoutForm);
      } else {
        await createWorkout(workoutForm);
      }
      setIsWorkoutFormOpen(false);
      fetchWorkouts();
    } catch (err) {
      setWorkoutFormError(err.message);
    } finally {
      setWorkoutSaving(false);
    }
  };

  const handleWorkoutDeleteClick = (workout) => {
    setSelectedWorkout(workout);
    setWorkoutDeleteError('');
    setIsWorkoutDeleteModalOpen(true);
  };

  const confirmWorkoutDelete = async () => {
    if (!selectedWorkout) return;

    try {
      await deleteWorkout(selectedWorkout.id);
      setIsWorkoutDeleteModalOpen(false);
      setSelectedWorkout(null);
      fetchWorkouts();
    } catch (err) {
      setWorkoutDeleteError(err.message);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getUsersByRole(activeTab.role);
      setUsers(data || []);
    } catch (err) {
      setError('Failed to fetch users: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateChange = (field, value) => {
    setCreateForm(f => ({ ...f, [field]: value }));
    setCreateError('');
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    setCreateLoading(true);
    setCreateError('');

    try {
      await createUser({
        ...createForm,
        role: activeTab.role
      });
      setIsCreateModalOpen(false);
      setCreateForm({ firstName: '', lastName: '', email: '', phone: '', password: '' });
      fetchUsers(); // Refresh list
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreateLoading(false);
    }
  };

  const handleDeleteClick = (user) => {
    setSelectedUser(user);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!selectedUser) return;
    
    try {
      await deleteUser(selectedUser.id);
      setIsDeleteModalOpen(false);
      setSelectedUser(null);
      fetchUsers(); // Refresh list
    } catch (err) {
      alert('Failed to delete: ' + err.message);
    }
  };

  return (
    <main className="admin-page">
      <div className="admin-header">
        <div className="admin-header-content">
          <div>
            <h1 className="admin-title">Admin <span>Dashboard</span></h1>
            <p className="admin-subtitle">Manage platform users, trainers, and gym owners</p>
          </div>
        </div>
      </div>

      <div className="admin-tabs-bar">
        <div className="admin-tabs-inner">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`admin-tab ${activeTab.id === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="admin-content">
        <div className="admin-controls">
          {activeTab.id === 'workouts' ? (
            <button className="btn-primary" onClick={openCreateWorkoutForm}>
              + Add Workout
            </button>
          ) : (
            <button className="btn-primary" onClick={() => setIsCreateModalOpen(true)}>
              + Create New {activeTab.label.replace(/s$/, '')}
            </button>
          )}
        </div>

        <div className="admin-card">
          {activeTab.id === 'workouts' ? (
            loading ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
            ) : error ? (
              <div style={{ padding: '40px', textAlign: 'center', color: '#ef4444' }}>{error}</div>
            ) : workouts.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No workouts found.</div>
            ) : (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Category</th>
                      <th>Description</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workouts.map(w => (
                      <tr key={w.id}>
                        <td>{w.name}</td>
                        <td>{w.category}</td>
                        <td>{w.description || '-'}</td>
                        <td>
                          <div className="admin-actions" style={{ justifyContent: 'flex-end' }}>
                            <button
                              className="admin-btn-icon"
                              title="Edit Workout"
                              onClick={() => openEditWorkoutForm(w)}
                            >
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                            </button>
                            <button
                              className="admin-btn-icon delete"
                              title="Delete Workout"
                              onClick={() => handleWorkoutDeleteClick(w)}
                            >
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
          ) : error ? (
            <div style={{ padding: '40px', textAlign: 'center', color: '#ef4444' }}>{error}</div>
          ) : users.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>No {activeTab.label.toLowerCase()} found.</div>
          ) : (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Status</th>
                    <th>Joined</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td>{u.firstName} {u.lastName}</td>
                      <td className="email">{u.email}</td>
                      <td>{u.phone || '-'}</td>
                      <td>
                        <span className={`admin-badge ${u.isEmailVerified ? 'verified' : 'unverified'}`}>
                          {u.isEmailVerified ? 'Verified' : 'Pending'}
                        </span>
                      </td>
                      <td className="date">{new Date(u.createdAt).toLocaleDateString()}</td>
                      <td>
                        <div className="admin-actions" style={{ justifyContent: 'flex-end' }}>
                          <button 
                            className="admin-btn-icon delete" 
                            title="Delete Account"
                            onClick={() => handleDeleteClick(u)}
                          >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {isCreateModalOpen && (
        <div className="admin-modal-overlay">
          <div className="admin-modal">
            <div className="admin-modal-header">
              <h3 className="admin-modal-title">Create {activeTab.label.replace(/s$/, '')}</h3>
              <p className="admin-modal-desc">Fill in the details to manually provision a new account.</p>
            </div>

            <form className="admin-form" onSubmit={handleCreateSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="admin-form-group">
                  <label>First Name</label>
                  <input required className="admin-input" value={createForm.firstName} onChange={e => handleCreateChange('firstName', e.target.value)} />
                </div>
                <div className="admin-form-group">
                  <label>Last Name</label>
                  <input required className="admin-input" value={createForm.lastName} onChange={e => handleCreateChange('lastName', e.target.value)} />
                </div>
              </div>

              <div className="admin-form-group">
                <label>Email Address</label>
                <input required type="email" className="admin-input" value={createForm.email} onChange={e => handleCreateChange('email', e.target.value)} />
              </div>

              <div className="admin-form-group">
                <label>Phone (Optional)</label>
                <input type="tel" className="admin-input" value={createForm.phone} onChange={e => handleCreateChange('phone', e.target.value)} />
              </div>

              <div className="admin-form-group">
                <label>Temporary Password</label>
                <input required type="password" minLength="8" className="admin-input" value={createForm.password} onChange={e => handleCreateChange('password', e.target.value)} />
              </div>

              {createError && <div style={{ color: '#ef4444', fontSize: '0.85rem' }}>{createError}</div>}

              <div className="admin-modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setIsCreateModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={createLoading}>
                  {createLoading ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && selectedUser && (
        <div className="admin-modal-overlay">
          <div className="admin-modal" style={{ maxWidth: '400px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            <div className="admin-modal-header" style={{ marginBottom: '16px' }}>
              <h3 className="admin-modal-title" style={{ color: '#ef4444' }}>Delete Account?</h3>
              <p className="admin-modal-desc">
                Are you sure you want to permanently delete <strong>{selectedUser.firstName} {selectedUser.lastName}</strong>? 
                This action cannot be undone.
              </p>
            </div>

            <div className="admin-modal-actions" style={{ borderTop: 'none', paddingTop: 0 }}>
              <button className="btn-secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</button>
              <button className="btn-primary" style={{ background: '#ef4444', borderColor: '#ef4444' }} onClick={confirmDelete}>
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Workout Modal */}
      {isWorkoutFormOpen && (
        <div className="admin-modal-overlay">
          <div className="admin-modal">
            <div className="admin-modal-header">
              <h3 className="admin-modal-title">{editingWorkout ? 'Edit Workout' : 'Add Workout'}</h3>
              <p className="admin-modal-desc">Manage the shared workout catalog users can schedule into their timetable.</p>
            </div>

            <form className="admin-form" onSubmit={handleWorkoutFormSubmit}>
              <div className="admin-form-group">
                <label>Name</label>
                <input
                  required
                  className="admin-input"
                  value={workoutForm.name}
                  onChange={e => setWorkoutForm(f => ({ ...f, name: e.target.value }))}
                  maxLength={100}
                />
              </div>

              <div className="admin-form-group">
                <label>Category</label>
                <input
                  required
                  className="admin-input"
                  value={workoutForm.category}
                  onChange={e => setWorkoutForm(f => ({ ...f, category: e.target.value }))}
                  maxLength={100}
                />
              </div>

              <div className="admin-form-group">
                <label>Description (Optional)</label>
                <input
                  className="admin-input"
                  value={workoutForm.description}
                  onChange={e => setWorkoutForm(f => ({ ...f, description: e.target.value }))}
                  maxLength={500}
                />
              </div>

              {workoutFormError && <div style={{ color: '#ef4444', fontSize: '0.85rem' }}>{workoutFormError}</div>}

              <div className="admin-modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setIsWorkoutFormOpen(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={workoutSaving}>
                  {workoutSaving ? 'Saving...' : 'Save Workout'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Workout Confirmation Modal */}
      {isWorkoutDeleteModalOpen && selectedWorkout && (
        <div className="admin-modal-overlay">
          <div className="admin-modal" style={{ maxWidth: '400px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            <div className="admin-modal-header" style={{ marginBottom: '16px' }}>
              <h3 className="admin-modal-title" style={{ color: '#ef4444' }}>Delete Workout?</h3>
              <p className="admin-modal-desc">
                Are you sure you want to permanently delete <strong>{selectedWorkout.name}</strong>?
                This action cannot be undone.
              </p>
              {workoutDeleteError && <p style={{ color: '#ef4444', fontSize: '0.85rem' }}>{workoutDeleteError}</p>}
            </div>

            <div className="admin-modal-actions" style={{ borderTop: 'none', paddingTop: 0 }}>
              <button className="btn-secondary" onClick={() => setIsWorkoutDeleteModalOpen(false)}>Cancel</button>
              <button className="btn-primary" style={{ background: '#ef4444', borderColor: '#ef4444' }} onClick={confirmWorkoutDelete}>
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
