import { Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import client from '../api/client'
import NewProjectModal from '../components/NewProjectModal'

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await client.get('/api/v1/projects/')
      setProjects(data)
    } catch {
      toast.error('Could not load projects')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="animate-fade-in">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
            Your projects
          </h1>
          <p className="mt-1 text-slate-500 dark:text-slate-400">
            Open a project to view and run generated test cases.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setModal(true)}
          className="btn-primary inline-flex items-center gap-2 self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          New project
        </button>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center dark:border-slate-800 dark:bg-[#12151c]">
          <p className="text-slate-500 dark:text-slate-400">Loading…</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/20">
          <p className="text-slate-600 dark:text-slate-300">No projects yet.</p>
          <button type="button" className="btn-primary mt-4" onClick={() => setModal(true)}>
            Create your first project
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link
              key={p._id || p.id}
              to={`/projects/${encodeURIComponent(p.name)}`}
              className="glass-card group block p-5 no-underline"
            >
              <h2 className="font-display text-lg font-semibold text-slate-900 group-hover:text-primary-600 dark:text-white dark:group-hover:text-primary-400">
                {p.name}
              </h2>
              {p.url ? (
                <p className="mt-2 truncate text-sm text-slate-500 dark:text-slate-400">{p.url}</p>
              ) : null}
              {p.description ? (
                <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">
                  {p.description}
                </p>
              ) : null}
            </Link>
          ))}
        </div>
      )}

      <NewProjectModal
        open={modal}
        onClose={() => setModal(false)}
        onComplete={() => load()}
      />
    </div>
  )
}
