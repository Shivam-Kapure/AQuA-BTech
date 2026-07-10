import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

export default function NeedsActionModal({
  open,
  onClose,
  projectName,
  testId,
  requiredInputs,
  onSubmitResume,
}) {
  const [values, setValues] = useState({})
  const [busy, setBusy] = useState(false)

  const fields = Array.isArray(requiredInputs) ? requiredInputs : []

  useEffect(() => {
    if (open) setValues({})
  }, [open, testId])

  if (!open) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await onSubmitResume?.(projectName, testId, values)
      toast.success('Inputs saved — re-running test')
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not resume test')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-80 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        aria-label="Close"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-[#141820]">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white">
              Supply required data
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              The test needs credentials or other values to continue (passed to the runner as
              environment variables).
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {fields.length === 0 ? (
            <p className="text-sm text-slate-500">No fields specified — add key/value pairs.</p>
          ) : (
            fields.map((f) => (
              <label key={f.name} className="block">
                <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  {f.name}
                </span>
                {f.hint ? (
                  <p className="mb-1 text-xs text-slate-400 dark:text-slate-500">{f.hint}</p>
                ) : null}
                <input
                  type="text"
                  autoComplete="off"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/30 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                  value={values[f.name] ?? ''}
                  onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
                />
              </label>
            ))
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={busy} className="btn-primary">
              {busy ? 'Submitting…' : 'Submit & re-run'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
