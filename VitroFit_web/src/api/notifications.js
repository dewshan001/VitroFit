import { apiAuthRequest } from './timetable';

/** Returns { items: [{ id, type, title, message, linkUrl, isRead, createdAt }], unreadCount }. */
export function getNotifications() {
  return apiAuthRequest('/notifications', 'GET');
}

export function markNotificationRead(id) {
  return apiAuthRequest(`/notifications/${id}/read`, 'POST');
}

export function markAllNotificationsRead() {
  return apiAuthRequest('/notifications/read-all', 'POST');
}
