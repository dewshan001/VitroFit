import { useState, useEffect } from 'react';

export function useAuth() {
  const [auth, setAuth] = useState(() => {
    try {
      const stored = localStorage.getItem('vitrofitAuth');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    const handleStorage = () => {
      try {
        const stored = localStorage.getItem('vitrofitAuth');
        setAuth(stored ? JSON.parse(stored) : null);
      } catch {
        setAuth(null);
      }
    };
    window.addEventListener('storage', handleStorage);
    // Also listen for custom auth events within the same tab
    window.addEventListener('vitrofit-auth-change', handleStorage);
    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener('vitrofit-auth-change', handleStorage);
    };
  }, []);

  const logout = () => {
    localStorage.removeItem('vitrofitAuth');
    setAuth(null);
    window.dispatchEvent(new Event('vitrofit-auth-change'));
  };

  const updateUser = (updates) => {
    const newAuth = { ...auth, user: { ...auth.user, ...updates } };
    localStorage.setItem('vitrofitAuth', JSON.stringify(newAuth));
    setAuth(newAuth);
    window.dispatchEvent(new Event('vitrofit-auth-change'));
  };

  /**
   * Derive a display full name from the DB fields (firstName + lastName).
   * Falls back gracefully if neither exists.
   */
  const getFullName = () => {
    if (!auth?.user) return '';
    const u = auth.user;
    // DB stores firstName / lastName (camelCase from JSON serialiser)
    const first = u.firstName || u.FirstName || '';
    const last  = u.lastName  || u.LastName  || '';
    if (first || last) return `${first} ${last}`.trim();
    // Legacy fallback for data already in localStorage before this fix
    return u.fullName || u.name || u.email?.split('@')[0] || '';
  };

  return { auth, isLoggedIn: !!auth, logout, updateUser, getFullName };
}
