import { X } from 'lucide-react'
import Badge from './Badge'

function priorityVariant(p) {
  const x = (p || '').toLowerCase()
  if (x === 'high') return 'priority_high'
  if (x === 'medium') return 'priority_medium'
  if (x === 'low') return 'priority_low'
  return 'priority_medium'
}

function statusVariant(s, needAction) {
  if (needAction) return 'need_action'
  const x = (s || '').toLowerCase()
  if (x === 'passed') return 'passed'
  if (x === 'failed') return 'failed'
  if (x === 'waiting') return 'waiting'
  return 'draft'
}

export default function TestCaseDetailModal({ test, open, onClose, needAction }) {
  if (!open || !test) return null

  const meta = test.metadata || {}
  const category = meta.category || test.tags?.[0] || '—'
  const priority = meta.priority || test.tags?.[1] || '—'
  const displayStatus = needAction ? 'Need action' : test.status || 'draft'

  const steps = (test.steps || []).map((s, i) => ({
    n: i + 1,
    action: typeof s.value === 'string' ? s.value : s.action || JSON.stringify(s),
    expected:
      i === (test.steps?.length || 1) - 1
        ? meta.expected_result || 'See expected results below'
        : '—',
  }))

  return (
    <div className="fixed inset-0 z-70 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close"
      />
      <div className="relative z-10 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-[#12151c]">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white/95 px-6 py-5 backdrop-blur dark:border-slate-700 dark:bg-[#12151c]/95">
          <div>
            <h2 className="font-display text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              {test.name}
            </h2>
            {test.description ? (
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{test.description}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid gap-4 p-6 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/40">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Category
            </p>
            <div className="mt-2">
              <Badge variant="category">{String(category).replace(/_/g, ' ')}</Badge>
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/40">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Priority
            </p>
            <div className="mt-2">
              <Badge variant={priorityVariant(priority)}>{priority}</Badge>
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/40">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Status
            </p>
            <div className="mt-2">
              <Badge variant={statusVariant(test.status, needAction)}>{displayStatus}</Badge>
            </div>
          </div>
        </div>

        <div className="px-6 pb-6">
          <h3 className="mb-4 font-display text-base font-bold text-slate-900 dark:text-white">
            Test steps
          </h3>
          <ul className="space-y-3">
            {steps.map((step) => (
              <li
                key={step.n}
                className="flex gap-4 rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-900/30"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-600 text-sm font-bold text-white shadow-sm shadow-primary-600/30">
                  {step.n}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-slate-900 dark:text-white">{step.action}</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Expected: {step.expected}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="border-t border-slate-200 px-6 py-5 dark:border-slate-700">
          <h3 className="mb-2 font-display text-base font-bold text-slate-900 dark:text-white">
            Expected results
          </h3>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-300">
            {meta.expected_result || 'Success criteria as defined by the generated test.'}
          </div>
        </div>
        {test.status === 'failed' && test.failure_reason ? (
          <div className="border-t border-slate-200 px-6 py-5 dark:border-slate-700">
            <h3 className="mb-2 font-display text-base font-bold text-slate-900 dark:text-white">
              Failure reason
            </h3>
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
              {test.failure_reason}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
