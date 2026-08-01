const API_ROOT = import.meta.env.VITE_API_ROOT ?? '/api/v1'

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, { headers: { Accept: 'application/json' } })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail?.message ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}
