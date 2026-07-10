import { Key, X } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/useAuthStore'

function JwtModalInner({ existing, onClose }) {
  const setRouteJwt = useAuthStore((s) => s.setRouteJwt)
  const [value, setValue] = useState(existing || '')

  const save = () => {
    setRouteJwt(value.trim())
    toast.success('Route JWT stored — sent as X-Aqua-Route-Jwt on test runs')
    onClose()
  }

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Key className="h-5 w-5 text-primary-600" />
          <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white">Route JWT</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
        Optional bearer token for protected routes. It is attached as the{' '}
        <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">X-Aqua-Route-Jwt</code>{' '}
        header when you run tests (your Playwright scripts can read{' '}
        <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">AQUA_ROUTE_JWT</code> from the
        environment).
      </p>
      <textarea
        rows={4}
        className="mb-4 w-full rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-sm text-slate-900 outline-none ring-primary-500/30 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
        placeholder="Paste JWT…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-secondary" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="btn-primary" onClick={save}>
          Save
        </button>
      </div>
    </>
  )
}

export default function JwtModal({ open, onClose }) {
  const existing = useAuthStore((s) => s.routeJwt)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <button type="button" className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-[#141820]">
        <JwtModalInner existing={existing} onClose={onClose} />
      </div>
    </div>
  )
}
