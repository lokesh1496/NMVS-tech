import api from './axios'

export const getMonitoringHistory = (limit = 100) => api.get('/monitoring/history', { params: { limit } }).then((r) => r.data)
export const getDeviceHistory = (ip, limit = 100) => api.get(`/monitoring/history/${encodeURIComponent(ip)}`, { params: { limit } }).then((r) => r.data)
export const checkDevice = (ip) => api.get(`/monitoring/check/${encodeURIComponent(ip)}`).then((r) => r.data)
