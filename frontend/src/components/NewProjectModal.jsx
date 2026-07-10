import { Loader2, X } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import client from '../api/client'

const PROFILES = [
  {
    id: 'quick',
    label: 'Quick test',
    hint: '~5 high-quality cases (happy path, edge, negative)',
    maxHint: 5,
  },
  {
    id: 'standard',
    label: 'Standard test',
    hint: '~10–15 cases',
    maxHint: 15,
  },
  {
    id: 'detailed',
    label: 'Detailed test',
    hint: '20+ comprehensive cases',
    maxHint: 24,
  },
]

export default function NewProjectModal({ open, onClose, onComplete }) {
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [prompt, setPrompt] = useState('')
  const [profile, setProfile] = useState('quick')
  const [busy, setBusy] = useState(false)
  const [genLabel, setGenLabel] = useState(1)

  if (!open) return null

  const selected = PROFILES.find((p) => p.id === profile) || PROFILES[0]

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim() || !url.trim()) {
      toast.error('Name and URL are required')
      return
    }
    setBusy(true)
    const max = selected.maxHint
    let tick = 1
    const interval = setInterval(() => {
      tick = Math.min(tick + 1, max)
      setGenLabel(tick)
    }, 700)
    try {
      await client.post('/api/v1/projects/', {
        name: name.trim(),
        url: url.trim(),
        description: prompt.trim() || undefined,
      })
      await client.post('/api/v1/generate/', {
        url: url.trim(),
        project_name: name.trim(),
        generation_profile: profile,
        user_prompt: prompt.trim() || undefined,
      })
      clearInterval(interval)
      toast.success('Test cases generated')
      onComplete?.({ name: name.trim() })
      setName('')
      setUrl('')
      setPrompt('')
      setProfile('quick')
      onClose()
    } catch (err) {
      clearInterval(interval)
      toast.error(err.response?.data?.detail || 'Could not create project or generate tests')
    } finally {
      setBusy(false)
      setGenLabel(1)
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <button type="button" className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-[#141820]">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="font-display text-xl font-bold text-slate-900 dark:text-white">
            New project
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {busy ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="h-12 w-12 animate-spin text-primary-600" />
            <p className="mt-6 text-center font-medium text-slate-800 dark:text-slate-200">
              Generating test case {genLabel}…
            </p>
            <p className="mt-2 text-center text-sm text-slate-500 dark:text-slate-400">
              Scraping the page, calling the LLM, and saving cases to your project.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Project name
              </span>
              <input
                required
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/30 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My app"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Target URL
              </span>
              <input
                required
                type="url"
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/30 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://…"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Short prompt (context)
              </span>
              <textarea
                rows={3}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/30 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="What should QA focus on?"
              />
            </label>
            <div>
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Test depth
              </span>
              <div className="mt-2 space-y-2">
                {PROFILES.map((p) => (
                  <label
                    key={p.id}
                    className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                      profile === p.id
                        ? 'border-primary-500 bg-primary-600/5 ring-1 ring-primary-500/30 dark:bg-primary-500/10'
                        : 'border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600'
                    }`}
                  >
                    <input
                      type="radio"
                      name="profile"
                      className="mt-1"
                      checked={profile === p.id}
                      onChange={() => setProfile(p.id)}
                    />
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">{p.label}</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{p.hint}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Create & generate
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
