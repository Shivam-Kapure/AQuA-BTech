// Turn any API error into a readable string for toasts. FastAPI's `detail` may be a
// string, a list of validation errors, or an object; rendering a non-string crashes React.
export function errorMessage(err, fallback = 'Something went wrong') {
  if (!err?.response) {
    return err?.code === 'ERR_NETWORK'
      ? 'Cannot reach the AQuA backend. Is it running on port 8000?'
      : err?.message || fallback
  }
  const data = err.response.data
  const detail = data?.detail ?? data?.error ?? data
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d) => {
        if (typeof d === 'string') return d
        const field = Array.isArray(d?.loc) ? d.loc.filter((p) => p !== 'body').join('.') : ''
        return field ? `${field}: ${d?.msg ?? ''}` : d?.msg ?? JSON.stringify(d)
      })
      .join('\n')
  }
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') return detail.message
  return fallback
}
