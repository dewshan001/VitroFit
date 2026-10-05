import { apiAuthRequest } from './timetable';

/** Reviewer queue for approved gym owners and admins. status: 'Pending' | 'Approved' | 'Rejected'. Returns { items, counts }. */
export function getTimetableReviews(status = 'Pending') {
  return apiAuthRequest(`/timetable-reviews?status=${encodeURIComponent(status)}`, 'GET');
}

export function getTimetableReview(id) {
  return apiAuthRequest(`/timetable-reviews/${id}`, 'GET');
}

export function approveTimetable(id, note) {
  return apiAuthRequest(`/timetable-reviews/${id}/approve`, 'POST', { note: note || null });
}

export function rejectTimetable(id, note) {
  return apiAuthRequest(`/timetable-reviews/${id}/reject`, 'POST', { note });
}
