import { useCallback, useEffect, useState } from 'react'

export function useRemote(loader, dependencies = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await loader())
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)
  useEffect(() => { reload() }, [reload])
  return { data, setData, loading, error, reload }
}
