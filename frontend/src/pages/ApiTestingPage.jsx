import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Save, ShieldCheck } from 'lucide-react'
import client from '../api/client'

const example = JSON.stringify({
  openapi: '3.0.3',
  info: { title: 'Example API', version: '1.0.0' },
  servers: [{ url: 'https://example.test' }],
  paths: { '/health': { get: { operationId: 'health', responses: { 200: { description: 'OK' } } } } },
}, null, 2)

const inputClass = 'mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900'

function operationUrl(spec, operation, pathValues) {
  const base = spec?.base_urls?.[0] || ''
  const path = operation.path.replace(/\{([^}]+)\}/g, (_, name) => encodeURIComponent(pathValues[name] || `{${name}}`))
  return `${base.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

function initialRequest(spec, operation) {
  const parameters = operation.parameters || []
  const pathValues = Object.fromEntries(parameters.filter((p) => p.in === 'path').map((p) => [p.name, p.example ?? p.default ?? '']))
  const query = Object.fromEntries(parameters.filter((p) => p.in === 'query').map((p) => [p.name, p.example ?? p.default ?? '']))
  const headers = Object.fromEntries(parameters.filter((p) => p.in === 'header').map((p) => [p.name, p.example ?? p.default ?? '']))
  return { pathValues, query, headers, body: '', authContext: { scheme: 'bearer', token: '' }, assertions: [] }
}

export default function ApiTestingPage() {
  const [document, setDocument] = useState(example)
  const [spec, setSpec] = useState(null)
  const [savedSpecs, setSavedSpecs] = useState([])
  const [selectedOperation, setSelectedOperation] = useState(null)
  const [request, setRequest] = useState(null)
  const [findings, setFindings] = useState([])
  const [savedFindings, setSavedFindings] = useState([])
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [workflow, setWorkflow] = useState([])
  const [runningOperation, setRunningOperation] = useState(null)
  const [activeJob, setActiveJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const selected = useMemo(() => spec?.operations?.find((item) => item.operation_id === selectedOperation), [spec, selectedOperation])

  useEffect(() => { loadSavedSpecs(); loadRuns(); loadFindings() }, [])

  async function loadSavedSpecs() {
    try { setSavedSpecs((await client.get('/api/v1/api-specs/')).data) } catch { /* optional on first use */ }
  }
  async function loadRuns() {
    try { setRuns((await client.get('/api/v1/api-specs/runs')).data) } catch { /* shown as empty */ }
  }
  async function loadFindings() {
    try { setSavedFindings((await client.get('/api/v1/api-specs/findings')).data) } catch { /* shown as empty */ }
  }

  async function parse() {
    setLoading(true)
    try {
      const { data } = await client.post('/api/v1/api-specs/parse', { document })
      setSpec(data); setSelectedOperation(data.operations[0]?.operation_id || null)
      setRequest(data.operations[0] ? initialRequest(data, data.operations[0]) : null)
      setFindings([]); toast.success(`Imported ${data.operations.length} operations`)
    } catch (error) { toast.error(error.response?.data?.detail || 'Could not parse OpenAPI document') } finally { setLoading(false) }
  }

  function chooseOperation(operation) {
    setSelectedOperation(operation.operation_id); setRequest(initialRequest(spec, operation))
  }

  async function saveSpec() {
    if (!spec) return
    setLoading(true)
    try { await client.post('/api/v1/api-specs/import', { document, project_name: spec.title }); await loadSavedSpecs(); toast.success('API specification saved') }
    catch (error) { toast.error(error.response?.data?.detail || 'Could not save API specification') } finally { setLoading(false) }
  }

  async function execute() {
    if (!spec || !selected || !request) return
    if (selected.path.includes('{') && Object.values(request.pathValues || {}).some((value) => !value)) { toast.error('Fill in all path parameters before running'); return }
    setRunningOperation(selected.operation_id)
    try {
      const body = request.body ? JSON.parse(request.body) : null
      const { data } = await client.post('/api/v1/api-specs/execute-async', {
        name: selected.operation_id, project_name: spec.title, method: selected.method,
        url: operationUrl(spec, selected, request.pathValues), headers: request.headers,
        query: request.query, body, auth_context: request.authContext, assertions: request.assertions,
      })
      setActiveJob({ id: data.job_id, status: 'queued', label: `${selected.operation_id} execution` })
      await pollJob(data.job_id, 120, `${selected.operation_id} execution`)
    } catch (error) { toast.error(error.response?.data?.detail || 'API execution failed') } finally { setRunningOperation(null) }
  }

  async function runWorkflow() {
    if (!workflow.length) return
    setLoading(true)
    try { const { data } = await client.post('/api/v1/api-specs/execute-workflow', workflow); setSelectedRun({ test_name: 'Workflow', result: data }); toast.success('Workflow completed') }
    catch (error) { toast.error(error.response?.data?.detail || 'Workflow failed') } finally { setLoading(false) }
  }

  async function pollJob(jobId, remaining = 120, successMessage = 'Job completed') {
    const { data } = await client.get(`/api/v1/api-specs/jobs/${jobId}`)
    setActiveJob(data.job)
    if (data.run) {
      setSelectedRun(data.run)
      setRuns((previous) => [data.run, ...previous.filter((run) => run.id !== data.run.id)])
      if (data.run.result?.findings) setFindings(data.run.result.findings)
    }
    if (['passed', 'failed', 'cancelled', 'warning'].includes(data.job.status)) {
      setActiveJob(null)
      await loadFindings()
      toast(data.job.status === 'passed' ? successMessage : `Job ${data.job.status}`)
      return
    }
    if (remaining <= 0) {
      setActiveJob(null)
      toast.error('Security scan status polling timed out')
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
    return pollJob(jobId, remaining - 1)
  }

  async function scan() {
    if (!spec) return
    setLoading(true)
    try {
      const { data } = await client.post('/api/v1/api-specs/security-scan-async', { spec, project_name: spec.title, active: false })
      setActiveJob({ id: data.job_id, status: 'queued' })
      await pollJob(data.job_id, 120, 'Passive security scan completed')
    }
    catch (error) { toast.error(error.response?.data?.detail || 'Security scan failed') } finally { setLoading(false) }
  }

  async function cancelActiveJob() {
    if (!activeJob?.id) return
    try { await client.post(`/api/v1/api-specs/jobs/${activeJob.id}/cancel`); setActiveJob(null); toast('Job cancelled') }
    catch (error) { toast.error(error.response?.data?.detail || 'Could not cancel security scan') }
  }

  async function updateFinding(finding, remediation_status) {
    try { const { data } = await client.patch(`/api/v1/api-specs/findings/${finding.id}`, { remediation_status, remediation_note: finding.remediation_note || null }); setSavedFindings((items) => items.map((item) => item.id === data.id ? data : item)) }
    catch (error) { toast.error(error.response?.data?.detail || 'Could not update finding') }
  }

  const updateRequest = (key, value) => setRequest((current) => ({ ...current, [key]: value }))
  const updateMap = (key, name, value) => setRequest((current) => ({ ...current, [key]: { ...current[key], [name]: value } }))
  const updateAssertion = (index, key, value) => setRequest((current) => ({ ...current, assertions: current.assertions.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item) }))
  const addWorkflowStep = () => {
    if (!selected || !request) return
    let body = null
    try { body = request.body ? JSON.parse(request.body) : null } catch { toast.error('Enter valid JSON before adding the workflow step'); return }
    setWorkflow((items) => [...items, { name: selected.operation_id, test_case: { name: selected.operation_id, project_name: spec.title, method: selected.method, url: operationUrl(spec, selected, request.pathValues), headers: request.headers, query: request.query, body, auth_context: request.authContext, assertions: request.assertions }, extract: {} }])
  }

  return (
    <div className="animate-fade-in space-y-6">
      <div><h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">API testing</h1><p className="mt-1 text-slate-500 dark:text-slate-400">Import, configure, execute, and review API workflows.</p></div>
      <section className="grid gap-5 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="glass-card p-5">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="openapi-document">OpenAPI JSON</label>
          <textarea id="openapi-document" value={document} onChange={(event) => setDocument(event.target.value)} className="mt-3 min-h-72 w-full rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-xs dark:border-slate-700 dark:bg-slate-900" />
          <div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={parse} disabled={loading || !!activeJob} className="btn-primary">{loading ? 'Working…' : 'Parse document'}</button><button type="button" onClick={saveSpec} disabled={!spec || loading || !!activeJob} className="btn-secondary"><Save className="mr-1 h-4 w-4" />Save</button><button type="button" onClick={scan} disabled={!spec || loading || !!activeJob} className="btn-secondary"><ShieldCheck className="mr-1 h-4 w-4" />Passive scan</button>{activeJob ? <button type="button" onClick={cancelActiveJob} className="rounded-lg border border-rose-300 px-3 py-2 text-sm font-semibold text-rose-700">Cancel job</button> : null}</div>
          {activeJob ? <p className="mt-2 text-xs text-slate-500">{activeJob.label || 'Job'} status: <span className="font-semibold">{activeJob.status}</span> · attempts {activeJob.attempts || 0}</p> : null}
          {savedSpecs.length ? <div className="mt-5"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Saved specifications</p><div className="mt-2 space-y-1">{savedSpecs.slice(0, 5).map((item) => <button key={item.id} type="button" className="block w-full rounded-lg px-2 py-1.5 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800" onClick={() => { setSpec(item); setDocument(JSON.stringify(item, null, 2)); setSelectedOperation(item.operations[0]?.operation_id || null); setRequest(item.operations[0] ? initialRequest(item, item.operations[0]) : null) }}>{item.title} v{item.version}</button>)}</div></div> : null}
        </div>
        <div className="glass-card p-5"><h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">Operations</h2>{!spec ? <p className="mt-5 text-sm text-slate-500">Parse a document to see operations.</p> : <div className="mt-4 space-y-2">{spec.operations.map((operation) => <button type="button" key={operation.operation_id} onClick={() => chooseOperation(operation)} className={`w-full rounded-xl border p-3 text-left ${selectedOperation === operation.operation_id ? 'border-primary-500 bg-primary-50/60 dark:bg-primary-950/20' : 'border-slate-200 dark:border-slate-700'}`}><div className="flex items-center gap-2"><span className="rounded bg-primary-100 px-2 py-0.5 text-xs font-bold text-primary-700">{operation.method}</span><span className="font-mono text-sm dark:text-slate-200">{operation.path}</span></div><p className="mt-2 text-xs text-slate-500">{operation.operation_id} · {operation.auth_schemes.length ? operation.auth_schemes.join(', ') : 'authentication not declared'}</p></button>)}</div>}</div>
      </section>
      {selected && request ? <section className="glass-card p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">Request editor</h2><p className="mt-1 font-mono text-xs text-slate-500">{selected.method} {operationUrl(spec, selected, request.pathValues)}</p></div><button type="button" onClick={execute} disabled={!!runningOperation} className="btn-primary">{runningOperation ? 'Running…' : 'Run operation'}</button></div><div className="mt-4 grid gap-4 md:grid-cols-2"><div><h3 className="text-sm font-semibold">Path parameters</h3>{(selected.parameters || []).filter((p) => p.in === 'path').map((parameter) => <label key={parameter.name} className="mt-2 block text-xs text-slate-500">{parameter.name}<input className={inputClass} value={request.pathValues[parameter.name] || ''} onChange={(event) => updateMap('pathValues', parameter.name, event.target.value)} /></label>)}</div><div><h3 className="text-sm font-semibold">Query parameters</h3>{(selected.parameters || []).filter((p) => p.in === 'query').map((parameter) => <label key={parameter.name} className="mt-2 block text-xs text-slate-500">{parameter.name}<input className={inputClass} value={request.query[parameter.name] || ''} onChange={(event) => updateMap('query', parameter.name, event.target.value)} /></label>)}</div><div><h3 className="text-sm font-semibold">Headers</h3><textarea className={`${inputClass} min-h-24 font-mono text-xs`} value={JSON.stringify(request.headers, null, 2)} onChange={(event) => { try { updateRequest('headers', JSON.parse(event.target.value)) } catch { /* keep current map until valid JSON */ } }} /></div><div><h3 className="text-sm font-semibold">JSON body</h3><textarea className={`${inputClass} min-h-24 font-mono text-xs`} placeholder="Optional JSON body" value={request.body} onChange={(event) => updateRequest('body', event.target.value)} /></div><div><h3 className="text-sm font-semibold">Authentication</h3><div className="mt-2 flex gap-2"><select className={inputClass} value={request.authContext.scheme} onChange={(event) => updateRequest('authContext', { ...request.authContext, scheme: event.target.value })}><option value="bearer">Bearer</option><option value="basic">Basic</option></select><input className={inputClass} type="password" placeholder="Token or encoded credentials" value={request.authContext.token} onChange={(event) => updateRequest('authContext', { ...request.authContext, token: event.target.value })} /></div><p className="mt-1 text-xs text-slate-500">The token is sent for this run and is redacted from stored evidence.</p></div><div><div className="flex items-center justify-between"><h3 className="text-sm font-semibold">Assertions</h3><button type="button" className="text-xs text-primary-600" onClick={() => updateRequest('assertions', [...request.assertions, { kind: 'status', expected: 200, path: null }])}>Add assertion</button></div>{request.assertions.map((assertion, index) => <div key={index} className="mt-2 grid grid-cols-3 gap-2"><select className={inputClass} value={assertion.kind} onChange={(event) => updateAssertion(index, 'kind', event.target.value)}><option value="status">Status</option><option value="header">Header</option><option value="json_field">JSON field</option><option value="content_type">Content type</option><option value="response_time_ms">Response time</option></select><input className={inputClass} placeholder="Expected" value={assertion.expected ?? ''} onChange={(event) => updateAssertion(index, 'expected', event.target.value)} /><input className={inputClass} placeholder="Path/header (optional)" value={assertion.path || ''} onChange={(event) => updateAssertion(index, 'path', event.target.value)} /></div>)}</div></div><button type="button" className="btn-secondary mt-4" onClick={addWorkflowStep}>Add to workflow</button></section> : null}
      {workflow.length ? <section className="glass-card p-5"><div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold">Workflow builder</h2><button type="button" onClick={runWorkflow} disabled={loading} className="btn-primary">Run workflow</button></div><div className="mt-3 space-y-2">{workflow.map((step, index) => <div key={`${step.name}-${index}`} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700"><div className="flex items-center justify-between"><span>{index + 1}. {step.name}</span><button type="button" className="text-xs text-rose-600" onClick={() => setWorkflow((items) => items.filter((_, itemIndex) => itemIndex !== index))}>Remove</button></div><div className="mt-2 grid gap-2 sm:grid-cols-2"><input className={inputClass} placeholder="Variable name, e.g. access_token" value={Object.keys(step.extract)[0] || ''} onChange={(event) => setWorkflow((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, extract: event.target.value ? { [event.target.value]: Object.values(item.extract)[0] || '$.token' } : {} } : item))} /><input className={inputClass} placeholder="JSONPath, e.g. $.token" value={Object.values(step.extract)[0] || ''} onChange={(event) => setWorkflow((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, extract: Object.keys(item.extract)[0] ? { [Object.keys(item.extract)[0]]: event.target.value } : {} } : item))} /></div></div>)}</div></section> : null}
      {selectedRun ? <section className="glass-card p-5"><div className="flex items-center justify-between"><h2 className="font-display text-lg font-semibold">Run detail</h2><button type="button" className="text-sm text-slate-500" onClick={() => setSelectedRun(null)}>Close</button></div><pre className="mt-3 max-h-80 overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(selectedRun, null, 2)}</pre></section> : null}
      <section className="grid gap-5 lg:grid-cols-2"><div className="glass-card p-5"><h2 className="font-display text-lg font-semibold">API run history</h2><div className="mt-3 space-y-2">{runs.length ? runs.map((run) => <button type="button" key={run.id} onClick={() => setSelectedRun(run)} className="flex w-full items-center justify-between rounded-lg border border-slate-200 p-3 text-left text-sm dark:border-slate-700"><span className="font-medium">{run.test_name}</span><span className={run.result?.passed ? 'text-emerald-600' : 'text-rose-600'}>{run.result?.passed ? 'passed' : 'failed'} · {run.result?.status_code ?? 'n/a'}</span></button>) : <p className="text-sm text-slate-500">No API runs yet.</p>}</div></div><div className="glass-card p-5"><h2 className="font-display text-lg font-semibold">Findings and remediation</h2><div className="mt-3 space-y-2">{[...findings, ...savedFindings].length ? [...findings, ...savedFindings].map((finding, index) => <div key={`${finding.id || finding.category}-${index}`} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700"><div className="flex items-center justify-between gap-3"><span className="font-semibold">{finding.category}</span>{finding.id ? <select className="rounded border border-slate-200 bg-transparent px-2 py-1 text-xs dark:border-slate-700" value={finding.remediation_status || 'open'} onChange={(event) => updateFinding(finding, event.target.value)}><option value="open">Open</option><option value="accepted">Accepted</option><option value="fixed">Fixed</option></select> : <span className="text-amber-600">new</span>}</div><p className="mt-1 text-slate-600 dark:text-slate-300">{finding.finding}</p></div>) : <p className="text-sm text-slate-500">Run a passive scan to create findings.</p>}</div></div></section>
    </div>
  )
}
