import { Loader2, Play, ShieldCheck } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import client from '../api/client'
import Badge from '../components/Badge'

function statusVariant(status) {
  const value = String(status || '').toLowerCase()
  if (value === 'pass' || value === 'passed') return 'passed'
  if (value === 'fail' || value === 'failed') return 'failed'
  if (value === 'warning') return 'waiting'
  return 'draft'
}

function severityVariant(severity) {
  const value = String(severity || '').toLowerCase()
  if (value === 'high' || value === 'critical') return 'priority_high'
  if (value === 'medium') return 'priority_medium'
  return 'priority_low'
}

export default function SecurityTestingPage() {
  const [projects, setProjects] = useState([])
  const [projectName, setProjectName] = useState('')
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [runningId, setRunningId] = useState(null)

  const selectedProject = useMemo(
    () => projects.find((project) => project.name === projectName) || null,
    [projectName, projects]
  )

  const loadProjects = useCallback(async () => {
    try {
      const { data } = await client.get('/api/v1/projects/')
      setProjects(data)
      setProjectName((current) => current || data[0]?.name || '')
    } catch {
      toast.error('Could not load projects')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadTests = useCallback(async () => {
    if (!projectName) {
      setTests([])
      return
    }
    try {
      const { data } = await client.get(`/api/v1/security/${encodeURIComponent(projectName)}`)
      setTests(data)
    } catch (error) {
      if (error.response?.status !== 404) toast.error('Could not load security tests')
      setTests([])
    }
  }, [projectName])

  useEffect(() => { loadProjects() }, [loadProjects])
  useEffect(() => { loadTests() }, [loadTests])

  const generate = async () => {
    if (!selectedProject?.url) {
      toast.error('Choose a project with a target URL first')
      return
    }
    setGenerating(true)
    try {
      await client.post('/api/v1/security/generate', {
        project_name: selectedProject.name,
        url: selectedProject.url,
      })
      toast.success('Security test cases are ready')
      await loadTests()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not generate security tests')
    } finally {
      setGenerating(false)
    }
  }

  const execute = async (testCase) => {
    setRunningId(testCase.test_id)
    try {
      const { data } = await client.post(`/api/v1/security/${encodeURIComponent(projectName)}/${encodeURIComponent(testCase.test_id)}/execute`)
      toast(data.status === 'PASS' ? 'Security test passed' : `Security test ${String(data.status).toLowerCase()}`)
      await loadTests()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not run security test')
    } finally {
      setRunningId(null)
    }
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">Security testing</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400">Generate defensive checks, run safe checkers, and review remediation guidance.</p>
      </div>
      <section className="glass-card flex flex-col gap-4 p-5 sm:flex-row sm:items-end sm:justify-between">
        <label className="block min-w-64 text-sm font-medium text-slate-700 dark:text-slate-200">
          Project
          <select className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900" value={projectName} onChange={(event) => setProjectName(event.target.value)}>
            {projects.length ? projects.map((project) => <option key={project.id || project._id || project.name} value={project.name}>{project.name}</option>) : <option value="">No projects available</option>}
          </select>
        </label>
        <button type="button" className="btn-primary inline-flex items-center gap-2" onClick={generate} disabled={generating || !selectedProject?.url}>
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
          {generating ? 'Generating…' : 'Generate security tests'}
        </button>
      </section>
      <section className="grid gap-4 lg:grid-cols-2">
        {loading ? <p className="text-sm text-slate-500">Loading projects…</p> : null}
        {!loading && !tests.length ? <p className="text-sm text-slate-500">No security tests yet. Generate defensive checks for the selected project.</p> : null}
        {tests.map((testCase) => (
          <article key={testCase.id || testCase.test_id} className="glass-card p-5">
            <div className="flex items-start justify-between gap-3"><div><p className="font-mono text-xs text-slate-500">{testCase.test_id}</p><h2 className="mt-1 font-display text-lg font-semibold text-slate-900 dark:text-white">{testCase.title}</h2></div><Badge variant={statusVariant(testCase.status)}>{testCase.status}</Badge></div>
            <div className="mt-3 flex flex-wrap gap-2"><Badge variant="category">{testCase.category}</Badge><Badge variant={severityVariant(testCase.severity)}>{testCase.severity}</Badge><span className="rounded-full bg-cyan-500/10 px-3 py-0.5 font-mono text-xs font-semibold text-cyan-800 dark:text-cyan-200">Decision {testCase.decision_score ?? '—'}/100</span></div>
            <dl className="mt-4 space-y-2 text-sm"><div><dt className="font-semibold">Target</dt><dd className="break-all text-slate-600 dark:text-slate-300">{testCase.target}</dd></div><div><dt className="font-semibold">Check type</dt><dd className="text-slate-600 dark:text-slate-300">{testCase.test_type.replace(/_/g, ' ')}{testCase.method ? ` · ${testCase.method}` : ''}{testCase.parameter ? ` · ${testCase.parameter}` : ''}</dd></div><div><dt className="font-semibold">Expected secure behavior</dt><dd className="text-slate-600 dark:text-slate-300">{testCase.expected_secure_behavior}</dd></div><div><dt className="font-semibold">Execution boundary</dt><dd className="text-slate-600 dark:text-slate-300">Runs the built-in defensive checker only; destructive probes are not available here.</dd></div>{testCase.finding ? <div><dt className="font-semibold">Finding</dt><dd className="text-slate-600 dark:text-slate-300">{testCase.finding}</dd></div> : null}{testCase.recommendation ? <div><dt className="font-semibold">Recommendation</dt><dd className="text-slate-600 dark:text-slate-300">{testCase.recommendation}</dd></div> : null}</dl>
            <button type="button" className="btn-secondary mt-5 inline-flex items-center gap-2" onClick={() => execute(testCase)} disabled={runningId === testCase.test_id}>
              {runningId === testCase.test_id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
              {runningId === testCase.test_id ? 'Running…' : 'Run safe check'}
            </button>
          </article>
        ))}
      </section>
    </div>
  )
}
