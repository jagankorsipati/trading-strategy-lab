import { useEffect, useState } from 'react'
import { apiGet } from './client'

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(path))

  useEffect(() => {
    if (!path) { setLoading(false); return }
    let active = true
    setLoading(true); setError(null)
    apiGet<T>(path)
      .then(value => { if (active) setData(value) })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Unable to load research artifact') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [path])
  return { data, error, loading }
}
