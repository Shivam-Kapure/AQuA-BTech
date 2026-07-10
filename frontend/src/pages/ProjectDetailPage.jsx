import {
  AlertCircle,
  ArrowLeft,
  Download,
  Key,
  Loader2,
  Play,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import client from '../api/client'
import Badge from '../components/Badge'
import JwtModal from '../components/JwtModal'
import NeedsActionModal from '../components/NeedsActionModal'
import TestCaseDetailModal from '../components/TestCaseDetailModal'
import aquaLogo from '../assets/aqua-logo.png'

function rowKey(tc) {
  return String(tc.metadata?.test_id || tc.id || '')
}

function priorityVariant(p) {
  const x = String(p || '').toLowerCase()
  if (x === 'high') return 'priority_high'
  if (x === 'medium') return 'priority_medium'
  if (x === 'low') return 'priority_low'
  return 'priority_medium'
}

function statusBadgeVariant(status, needAction) {
  if (needAction) return 'need_action'
  const s = String(status || '').toLowerCase()
  if (s === 'passed') return 'passed'
  if (s === 'failed') return 'failed'
  if (s === 'waiting') return 'waiting'
  if (s === 'draft' || s === 'ready' || s === 'archived') return 'draft'
  return 'draft'
}

function formatDuration(ms) {
  if (ms == null || Number.isNaN(ms)) return '—'
  return `${Math.round(ms)}ms`
}

function getResultLabel(status) {
  return String(status || '').toLowerCase() === 'passed' ? 'Passed' : 'Not Passed'
}

function safeStepText(step, i) {
  if (typeof step?.value === 'string') return `${i + 1}. ${step.value}`
  if (typeof step?.action === 'string') return `${i + 1}. ${step.action}`
  try {
    return `${i + 1}. ${JSON.stringify(step)}`
  } catch {
    return `${i + 1}. [unserializable step]`
  }
}

function toDataUrl(src) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Could not read image'))
    fetch(src)
      .then((r) => r.blob())
      .then((blob) => reader.readAsDataURL(blob))
      .catch(reject)
  })
}

export default function ProjectDetailPage() {
  const { projectName: rawName } = useParams()
  const projectName = useMemo(() => decodeURIComponent(rawName || ''), [rawName])

  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [jwtOpen, setJwtOpen] = useState(false)
  const [needsModal, setNeedsModal] = useState({ open: false, testId: null, inputs: [] })

  /** @type {Record<string, { phase: string, durationMs?: number, requiredInputs?: any[], lastStatus?: string, lastFailureReason?: string }>} */
  const [runState, setRunState] = useState({})

  const loadTests = useCallback(async () => {
    if (!projectName) return
    setLoading(true)
    try {
      const { data } = await client.get(`/api/v1/test-cases/${encodeURIComponent(projectName)}`)
      setTests(data)
    } catch {
      toast.error('Could not load test cases')
    } finally {
      setLoading(false)
    }
  }, [projectName])

  useEffect(() => {
    loadTests()
  }, [loadTests])

  const runTest = async (tc, e) => {
    e?.stopPropagation()
    const key = rowKey(tc)
    if (!key) {
      toast.error('Missing test id')
      return
    }
    const t0 = Date.now()
    setRunState((s) => ({
      ...s,
      [key]: { phase: 'generating_script', requiredInputs: undefined },
    }))

    const flip = setTimeout(() => {
      setRunState((s) => {
        const cur = s[key]
        if (!cur || cur.phase !== 'generating_script') return s
        return { ...s, [key]: { ...cur, phase: 'testing' } }
      })
    }, 2200)

    try {
      const { data } = await client.post(
        `/api/v1/${encodeURIComponent(projectName)}/${encodeURIComponent(key)}`
      )
      clearTimeout(flip)
      const durationMs = Date.now() - t0
      setRunState((s) => ({
        ...s,
        [key]: {
          phase: 'idle',
          durationMs,
          requiredInputs: data.required_inputs || undefined,
          lastStatus: data.status,
          lastFailureReason: data.failure_reason || undefined,
        },
      }))
      if (data.status === 'failed' && data.failure_reason) {
        toast.error(data.failure_reason.slice(0, 120))
      }
      await loadTests()
    } catch (err) {
      clearTimeout(flip)
      const msg = err.response?.data?.detail || 'Test run failed'
      toast.error(typeof msg === 'string' ? msg : 'Test run failed')
      setRunState((s) => ({
        ...s,
        [key]: {
          phase: 'idle',
          durationMs: Date.now() - t0,
          lastStatus: 'failed',
          lastFailureReason: typeof msg === 'string' ? msg : 'Test run failed',
        },
      }))
    }
  }

  const resumeTest = async (project, testId, inputs) => {
    const key = String(testId || '')
    if (!key) {
      throw new Error('Missing test id')
    }

    const t0 = Date.now()
    setRunState((s) => ({
      ...s,
      [key]: { phase: 'generating_script', requiredInputs: undefined },
    }))

    const flip = setTimeout(() => {
      setRunState((s) => {
        const cur = s[key]
        if (!cur || cur.phase !== 'generating_script') return s
        return { ...s, [key]: { ...cur, phase: 'testing' } }
      })
    }, 2200)

    try {
      const enc = encodeURIComponent(project)
      const { data } = await client.post(`/api/v1/${enc}/${encodeURIComponent(key)}/resume`, {
        inputs: inputs || {},
      })
      clearTimeout(flip)
      const durationMs = Date.now() - t0
      setRunState((s) => ({
        ...s,
        [key]: {
          phase: 'idle',
          durationMs,
          requiredInputs: data.required_inputs || undefined,
          lastStatus: data.status,
          lastFailureReason: data.failure_reason || undefined,
        },
      }))
      if (data.status === 'failed' && data.failure_reason) {
        toast.error(data.failure_reason.slice(0, 120))
      }
      await loadTests()
    } catch (err) {
      clearTimeout(flip)
      const msg = err.response?.data?.detail || 'Could not resume test'
      setRunState((s) => ({
        ...s,
        [key]: {
          phase: 'idle',
          durationMs: Date.now() - t0,
          lastStatus: 'failed',
          lastFailureReason: typeof msg === 'string' ? msg : 'Could not resume test',
        },
      }))
      throw err
    }
  }

  const displayId = (tc) => {
    const tid = tc.metadata?.test_id
    if (tid) return String(tid).toLowerCase()
    const id = tc.id || tc._id
    return id ? `tc-${String(id).slice(-6)}` : '—'
  }

  const rowStatus = (tc) => {
    const key = rowKey(tc)
    const rs = runState[key]
    if (rs?.phase === 'generating_script') return { label: 'Generating script', variant: 'running' }
    if (rs?.phase === 'testing') return { label: 'Testing…', variant: 'running' }
    const st = tc.status
    if (st === 'waiting') return { label: 'Need action', variant: 'need_action' }
    return {
      label: st || 'draft',
      variant: statusBadgeVariant(st, false),
    }
  }

  const exportReport = async () => {
    try {
      if (!tests.length) {
        toast.error('No test cases to export')
        return
      }
      toast('Generating PDF report...')

      const doc = new jsPDF({ unit: 'pt', format: 'a4' })
      const generatedAt = new Date().toLocaleString()
      const safeProject = String(projectName || 'project').replace(/[^\w-]+/g, '_')
      const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
      const pageWidth = doc.internal.pageSize.getWidth()
      const pageHeight = doc.internal.pageSize.getHeight()

      const passed = tests.filter((tc) => String(tc.status || '').toLowerCase() === 'passed').length
      const failed = tests.filter((tc) => String(tc.status || '').toLowerCase() === 'failed').length
      const coverage = tests.length ? Math.round((passed / tests.length) * 100) : 0

      try {
        const logoDataUrl = await toDataUrl(aquaLogo)
        doc.addImage(logoDataUrl, 'PNG', 40, 28, 30, 30)
      } catch {
        // Export should still succeed even if logo embedding fails.
      }

      doc.setFillColor(15, 23, 42)
      doc.rect(0, 0, pageWidth, 82, 'F')
      doc.setTextColor(255, 255, 255)
      doc.setFontSize(18)
      doc.setFont('helvetica', 'bold')
      doc.text('AQUA QA TECHNICAL REPORT', 80, 46)
      doc.setFontSize(10)
      doc.setFont('helvetica', 'normal')
      doc.text(`Generated: ${generatedAt}`, 80, 64)
      doc.text(`Project: ${projectName || 'Unknown'}`, pageWidth - 40, 64, { align: 'right' })

      doc.setTextColor(30, 41, 59)
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(11)
      doc.text('Execution Summary', 40, 108)

      const metricTop = 118
      const metricHeight = 42
      const metricWidth = (pageWidth - 100) / 4
      const metrics = [
        { label: 'Total', value: String(tests.length), color: [37, 99, 235] },
        { label: 'Passed', value: String(passed), color: [22, 163, 74] },
        { label: 'Failed', value: String(failed), color: [220, 38, 38] },
        { label: 'Coverage', value: `${coverage}%`, color: [124, 58, 237] },
      ]
      metrics.forEach((m, i) => {
        const x = 40 + i * (metricWidth + 6)
        doc.setFillColor(248, 250, 252)
        doc.setDrawColor(226, 232, 240)
        doc.roundedRect(x, metricTop, metricWidth, metricHeight, 6, 6, 'FD')
        doc.setTextColor(m.color[0], m.color[1], m.color[2])
        doc.setFont('helvetica', 'bold')
        doc.setFontSize(14)
        doc.text(m.value, x + 10, metricTop + 18)
        doc.setTextColor(71, 85, 105)
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9)
        doc.text(m.label, x + 10, metricTop + 33)
      })

      doc.setFont('courier', 'normal')
      doc.setFontSize(9)
      doc.setTextColor(100, 116, 139)
      doc.text(
        `Legend: "Not Passed" includes failed, waiting, draft and unexecuted test cases.`,
        40,
        176
      )

      const rows = tests.map((tc, idx) => {
        const testCaseId = tc.metadata?.test_id || tc.id || `TC-${idx + 1}`
        const steps = (tc.steps || []).map((step, i) => safeStepText(step, i)).join('\n')
        const status = String(tc.status || '').toLowerCase()
        const failureReason =
          status === 'failed'
            ? String(tc.failure_reason || 'No failure reason provided')
            : '—'

        return [
          String(testCaseId),
          String(tc.name || 'Untitled'),
          getResultLabel(status),
          failureReason,
          steps || 'No steps',
        ]
      })

      autoTable(doc, {
      startY: 188,
      head: [['Test Case ID', 'Test Name', 'Result', 'Failure Reason', 'Steps']],
      body: rows,
      styles: {
        fontSize: 8.5,
        cellPadding: 6,
        valign: 'top',
        lineColor: [226, 232, 240],
        lineWidth: 0.5,
        textColor: [15, 23, 42],
      },
      headStyles: {
        fillColor: [30, 41, 59],
        textColor: [248, 250, 252],
        fontStyle: 'bold',
      },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      columnStyles: {
        0: { cellWidth: 70, fontStyle: 'bold' },
        1: { cellWidth: 96 },
        2: { cellWidth: 60 },
        3: { cellWidth: 110 },
        4: { cellWidth: 'auto' },
      },
      margin: { left: 40, right: 40 },
      didParseCell: (data) => {
        if (data.section === 'body' && data.column.index === 2) {
          const v = String(data.cell.raw || '')
          if (v === 'Passed') {
            data.cell.styles.textColor = [22, 163, 74]
            data.cell.styles.fontStyle = 'bold'
          } else {
            data.cell.styles.textColor = [220, 38, 38]
            data.cell.styles.fontStyle = 'bold'
          }
        }
        if (data.section === 'body' && data.column.index === 3) {
          const v = String(data.cell.raw || '')
          if (v !== '—') {
            data.cell.styles.textColor = [185, 28, 28]
          } else {
            data.cell.styles.textColor = [100, 116, 139]
          }
        }
      },
      didDrawPage: () => {
        const page = doc.getCurrentPageInfo().pageNumber
        doc.setDrawColor(226, 232, 240)
        doc.line(40, pageHeight - 28, pageWidth - 40, pageHeight - 28)
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(8)
        doc.setTextColor(100, 116, 139)
        doc.text('AQUA Agentic QA - Confidential Technical Report', 40, pageHeight - 14)
        doc.text(`Page ${page}`, pageWidth - 40, pageHeight - 14, { align: 'right' })
      },
    })

      doc.save(`${safeProject}_test_report_${stamp}.pdf`)
    } catch (err) {
      const message = err?.message || 'Failed to generate PDF report'
      toast.error(message)
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <Link
            to="/projects"
            className="mt-1 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
              {projectName}
            </h1>
            <p className="mt-1 text-slate-500 dark:text-slate-400">Test cases for this project</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary inline-flex items-center gap-2" onClick={() => setJwtOpen(true)}>
            <Key className="h-4 w-4" />
            Route JWT
          </button>
          <button type="button" className="btn-primary inline-flex items-center gap-2" onClick={exportReport}>
            <Download className="h-4 w-4" />
            Export PDF Report
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-[#12151c]">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/90 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400">
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Duration</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-16 text-center text-slate-500">
                    Loading test cases…
                  </td>
                </tr>
              ) : tests.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-16 text-center text-slate-500">
                    No test cases yet. Generate from the projects list.
                  </td>
                </tr>
              ) : (
                tests.map((tc) => {
                  const key = rowKey(tc)
                  const meta = tc.metadata || {}
                  const cat = meta.category || tc.tags?.[0] || '—'
                  const pri = meta.priority || tc.tags?.[1] || '—'
                  const rs = runState[key]
                  const st = rowStatus(tc)
                  const failureReason =
                    st.label.toLowerCase() === 'failed'
                      ? rs?.lastFailureReason || tc.failure_reason
                      : undefined

                  return (
                    <tr
                      key={key}
                      className="cursor-pointer border-b border-slate-100 transition hover:bg-slate-50/80 dark:border-slate-800/80 dark:hover:bg-slate-900/40"
                      onClick={() => setSelected(tc)}
                    >
                      <td className="px-4 py-3 font-mono text-slate-500 dark:text-slate-400">
                        {displayId(tc)}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-white">{tc.name}</td>
                      <td className="px-4 py-3">
                        <Badge variant="category">{String(cat).replace(/_/g, ' ')}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={priorityVariant(pri)}>{pri}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="space-y-1">
                          <span className="inline-flex items-center gap-2">
                            {rs?.phase === 'generating_script' || rs?.phase === 'testing' ? (
                              <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
                            ) : null}
                            <Badge variant={st.variant}>{st.label}</Badge>
                          </span>
                          {failureReason ? (
                            <p
                              className="max-w-xs truncate text-xs text-red-600 dark:text-red-300"
                              title={failureReason}
                            >
                              {failureReason}
                            </p>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                        {formatDuration(rs?.durationMs)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-wrap justify-end gap-2">
                          {tc.status === 'waiting' ? (
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-800 dark:text-amber-200"
                              onClick={(e) => {
                                e.stopPropagation()
                                const fallback = [
                                  {
                                    name: 'TEST_USERNAME',
                                    hint: 'Username or email for the app under test',
                                  },
                                  {
                                    name: 'TEST_PASSWORD',
                                    hint: 'Password for the app under test',
                                  },
                                ]
                                setNeedsModal({
                                  open: true,
                                  testId: key,
                                  inputs:
                                    rs?.requiredInputs?.length > 0 ? rs.requiredInputs : fallback,
                                })
                              }}
                            >
                              <AlertCircle className="h-3.5 w-3.5" />
                              Need action
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700"
                            onClick={(e) => runTest(tc, e)}
                          >
                            <Play className="h-3.5 w-3.5 fill-current" />
                            Test
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <TestCaseDetailModal
        test={selected}
        open={!!selected}
        onClose={() => setSelected(null)}
        needAction={!!selected && selected.status === 'waiting'}
      />

      <NeedsActionModal
        open={needsModal.open}
        onClose={() => setNeedsModal((m) => ({ ...m, open: false }))}
        projectName={projectName}
        testId={needsModal.testId}
        requiredInputs={needsModal.inputs}
        onSubmitResume={resumeTest}
      />

      <JwtModal open={jwtOpen} onClose={() => setJwtOpen(false)} />
    </div>
  )
}
