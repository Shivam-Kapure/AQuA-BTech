import clsx from 'clsx'

const variants = {
  category: 'bg-blue-600/15 text-blue-700 ring-1 ring-blue-600/25 dark:bg-blue-500/20 dark:text-blue-300 dark:ring-blue-400/30',
  priority_high: 'bg-amber-600/15 text-amber-800 ring-1 ring-amber-600/25 dark:bg-amber-500/20 dark:text-amber-200 dark:ring-amber-400/30',
  priority_medium: 'bg-slate-500/15 text-slate-700 ring-1 ring-slate-500/20 dark:bg-slate-400/15 dark:text-slate-200 dark:ring-slate-500/25',
  priority_low: 'bg-slate-400/10 text-slate-600 ring-1 ring-slate-400/20 dark:text-slate-400',
  passed: 'bg-emerald-600/15 text-emerald-800 ring-1 ring-emerald-600/25 dark:bg-emerald-500/20 dark:text-emerald-200 dark:ring-emerald-400/30',
  failed: 'bg-red-600/15 text-red-800 ring-1 ring-red-600/25 dark:bg-red-500/20 dark:text-red-200 dark:ring-red-400/30',
  waiting: 'bg-amber-500/15 text-amber-900 ring-1 ring-amber-500/30 dark:bg-amber-400/15 dark:text-amber-100 dark:ring-amber-400/25',
  need_action: 'bg-yellow-500/20 text-yellow-900 ring-1 ring-yellow-500/40 dark:bg-yellow-400/15 dark:text-yellow-100 dark:ring-yellow-400/30',
  draft: 'bg-slate-500/10 text-slate-600 ring-1 ring-slate-400/20 dark:text-slate-400',
  running: 'bg-primary-600/15 text-primary-800 ring-1 ring-primary-600/25 dark:bg-primary-500/20 dark:text-primary-200',
}

export default function Badge({ children, variant = 'category', className }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-3 py-0.5 text-xs font-semibold capitalize',
        variants[variant] || variants.category,
        className
      )}
    >
      {children}
    </span>
  )
}
