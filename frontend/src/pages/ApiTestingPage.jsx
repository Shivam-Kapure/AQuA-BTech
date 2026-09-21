import { useState } from 'react'
import toast from 'react-hot-toast'
import client from '../api/client'

const example = JSON.stringify({
  openapi: '3.0.3',
  info: { title: 'Example API', version: '1.0.0' },
  paths: { '/health': { get: { operationId: 'health', responses: { 200: { description: 'OK' } } } } },
}, null, 2)

export default function ApiTestingPage() {
  const [document, setDocument] = useState(example)
  const [spec, setSpec] = useState(null)
  const [findings, setFindings] = useState([])
  const [loading, setLoading] = useState(false)

  async function parse() {
    setLoading(true)
    try {
      const { data } = await client.post('/api/v1/api-specs/parse', { document })
      setSpec(data)
      setFindings([])
      toast.success(`Imported ${data.operations.length} operations`)
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not parse OpenAPI document')
    } finally {
      setLoading(false)
    }
  }

  async function scan() {
    if (!spec) return
    setLoading(true)
    try {
      const { data } = await client.post('/api/v1/api-specs/security-scan', { spec, active: false })
      setFindings(data)
      toast.success(`Found ${data.length} passive findings`)
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Security scan failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">API testing</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400">Import an OpenAPI document and inspect its normalized operation catalog.</p>
      </div>
      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="glass-card p-5">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="openapi-document">OpenAPI JSON</label>
          <textarea id="openapi-document" value={document} onChange={(event) => setDocument(event.target.value)} className="mt-3 min-h-80 w-full rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-900" />
          <button type="button" onClick={parse} disabled={loading} className="btn-primary mt-3">{loading ? 'Working…' : 'Parse document'}</button>
        </div>
        <div className="glass-card p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">Operations</h2>
            <button type="button" onClick={scan} disabled={!spec || loading} className="btn-secondary">Passive security scan</button>
          </div>
          {!spec ? <p className="mt-5 text-sm text-slate-500">Parse a document to see operations.</p> : (
            <div className="mt-4 space-y-2">
              {spec.operations.map((operation) => (
                <div key={operation.operation_id} className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                  <div className="flex items-center gap-2"><span className="rounded bg-primary-100 px-2 py-0.5 text-xs font-bold text-primary-700">{operation.method}</span><span className="font-mono text-sm dark:text-slate-200">{operation.path}</span></div>
                  <p className="mt-1 text-xs text-slate-500">{operation.operation_id} · {operation.auth_schemes.length ? operation.auth_schemes.join(', ') : 'authentication not declared'}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
      {findings.length > 0 ? <section className="glass-card p-5"><h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">Passive findings</h2><div className="mt-3 space-y-2">{findings.map((finding, index) => <div key={`${finding.operation_id}-${finding.category}-${index}`} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200"><span className="font-semibold">{finding.category}</span> · {finding.finding}</div>)}</div></section> : null}
    </div>
  )
}
