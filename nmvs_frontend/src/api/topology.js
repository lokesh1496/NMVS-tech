import api from './axios'

export const getTopology = (params = {}) => api.get('/topology/graph', { params }).then((r) => r.data)
export const getDiscoveryTopology = (network, autoRegister = false) =>
  api.get('/topology/discovery', { params: { network, auto_register: autoRegister } }).then((r) => r.data)
