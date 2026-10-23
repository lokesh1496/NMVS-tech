import api from './axios'

export const scanNetwork = (network) => api.get('/discovery/scan', { params: { network } }).then((r) => r.data)
export const pingAddress = (ip) => api.get(`/discovery/ping/${encodeURIComponent(ip)}`).then((r) => r.data)
