import api from './axios'

export const runSpeedTest = async (ip = 'internet') => {
  const { data: job } = await api.post('/speed-monitoring/local-jobs', { ip })
  const startedAt = Date.now()
  let result = job

  while (Date.now() - startedAt < 160000 && ['pending', 'running'].includes(result.status)) {
    await new Promise((resolve) => window.setTimeout(resolve, 2000))
    const response = await api.get(`/speed-monitoring/local-jobs/${job.job_id}`)
    result = response.data
  }

  if (result.status !== 'completed') {
    throw new Error(
      result.error_message ||
      (['pending', 'running'].includes(result.status)
        ? 'Local Agent did not finish the speed test in time.'
        : `Speed test ${result.status}.`),
    )
  }

  return result
}
export const getSpeedHistory = (limit = 20) => api.get('/speed-monitoring/history', { params: { limit } }).then((r) => r.data)
export const deleteSpeedHistory = (id) => api.delete(`/speed-monitoring/history/${id}`).then((r) => r.data)
