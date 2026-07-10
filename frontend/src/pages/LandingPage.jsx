import {
  ArrowRight,
  Bot,
  Layers,
  Play,
  Shield,
  Sparkles,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import ThemeToggle from '../components/ThemeToggle'
import aquaLogo from '../assets/aqua-logo.png'

const features = [
  {
    icon: Sparkles,
    title: 'LLM-powered cases',
    description:
      'Turn any URL into structured test scenarios—happy paths, edge cases, and negatives grounded in the real DOM.',
  },
  {
    icon: Play,
    title: 'Playwright execution',
    description:
      'Scripts are generated and run for you. See pass, fail, or waiting states with clear feedback and artifacts.',
  },
  {
    icon: Layers,
    title: 'Project workspaces',
    description:
      'Organize targets by project, generate at quick, standard, or depth you need, and run tests on demand.',
  },
  {
    icon: Shield,
    title: 'Protected flows',
    description:
      'Supply credentials when the agent asks, attach route JWTs for auth-heavy apps—all wired through the API.',
  },
  {
    icon: Bot,
    title: 'Agent orchestration',
    description:
      'Optional agent step decides when to expand coverage so you are not stuck in one-off manual loops.',
  },
  {
    icon: Zap,
    title: 'Fast iteration',
    description:
      'Dark and light themes, a focused UI, and a stack built for demos, coursework, and serious spikes alike.',
  },
]

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900 dark:bg-[#060a12] dark:text-slate-100">
      {/* Background */}
      <div
        className="pointer-events-none absolute inset-0 opacity-40 dark:opacity-30"
        aria-hidden
      >
        <div className="absolute -left-1/4 top-0 h-[520px] w-[520px] rounded-full bg-primary-500/30 blur-[120px] dark:bg-primary-600/25" />
        <div className="absolute -right-1/4 top-1/3 h-[480px] w-[480px] rounded-full bg-violet-500/20 blur-[100px] dark:bg-violet-600/15" />
        <div className="absolute bottom-0 left-1/3 h-[360px] w-[360px] rounded-full bg-cyan-500/15 blur-[90px] dark:bg-cyan-500/10" />
      </div>
      <div
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:64px_64px] dark:bg-[linear-gradient(to_right,#ffffff06_1px,transparent_1px),linear-gradient(to_bottom,#ffffff06_1px,transparent_1px)]"
        aria-hidden
      />

      {/* Nav */}
      <header className="relative z-20 border-b border-slate-200/60 bg-white/70 backdrop-blur-xl dark:border-slate-800/80 dark:bg-[#060a12]/75">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 md:px-8">
          <Link to="/" className="flex items-center gap-3 no-underline">
            <img src={aquaLogo} alt="AQUA logo" className="h-10 w-auto object-contain" />
            <span className="font-display text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              AQUA
            </span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle />
            <Link
              to="/login"
              className="rounded-xl px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
            >
              Sign in
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-primary-600/25 transition hover:bg-primary-700"
            >
              Get started
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main className="relative z-10">
        {/* Hero */}
        <section className="mx-auto max-w-6xl px-4 pb-20 pt-16 md:px-8 md:pb-28 md:pt-24">
          <div className="mx-auto max-w-3xl text-center">
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary-500/20 bg-primary-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-primary-700 dark:border-primary-400/25 dark:bg-primary-500/15 dark:text-primary-300">
              <Sparkles className="h-3.5 w-3.5" />
              Agentic QA platform
            </p>
            <h1 className="font-display text-4xl font-bold leading-[1.1] tracking-tight text-slate-900 dark:text-white md:text-6xl md:leading-[1.08]">
              Ship with confidence.{' '}
              <span className="bg-gradient-to-r from-primary-600 via-cyan-500 to-violet-500 bg-clip-text text-transparent dark:from-primary-400 dark:via-cyan-400 dark:to-violet-400">
                Test smarter.
              </span>
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-slate-600 dark:text-slate-400">
              AQUA combines browser intelligence, large language models, and Playwright so you can
              go from a URL to runnable UI tests in minutes—not days.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Link
                to="/login"
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-primary-600 px-8 py-3.5 text-base font-semibold text-white shadow-xl shadow-primary-600/25 transition hover:bg-primary-700 sm:w-auto"
              >
                Start free
                <ArrowRight className="h-5 w-5" />
              </Link>
              <a
                href="#features"
                className="inline-flex w-full items-center justify-center rounded-2xl border border-slate-300 bg-white/80 px-8 py-3.5 text-base font-semibold text-slate-800 backdrop-blur transition hover:border-slate-400 hover:bg-white dark:border-slate-600 dark:bg-slate-900/60 dark:text-slate-100 dark:hover:bg-slate-800 sm:w-auto"
              >
                Explore features
              </a>
            </div>
          </div>

          {/* Hero visual */}
          <div className="mx-auto mt-16 max-w-4xl">
            <div className="relative rounded-3xl border border-slate-200/80 bg-white/60 p-1 shadow-2xl shadow-slate-900/10 backdrop-blur dark:border-slate-700/80 dark:bg-slate-900/40 dark:shadow-black/40">
              <div className="overflow-hidden rounded-[1.35rem] bg-gradient-to-b from-slate-100 to-white dark:from-slate-900 dark:to-[#0c1018]">
                <div className="flex items-center gap-2 border-b border-slate-200/80 px-4 py-3 dark:border-slate-700/80">
                  <span className="h-3 w-3 rounded-full bg-red-400/90" />
                  <span className="h-3 w-3 rounded-full bg-amber-400/90" />
                  <span className="h-3 w-3 rounded-full bg-emerald-400/90" />
                  <span className="ml-4 font-mono text-xs text-slate-400">aqua.app / projects</span>
                </div>
                <div className="grid gap-4 p-6 md:grid-cols-2 md:p-8">
                  <div className="space-y-3 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
                    <p className="text-xs font-semibold uppercase tracking-wide text-primary-600 dark:text-primary-400">
                      Live run
                    </p>
                    <p className="font-display text-lg font-semibold text-slate-900 dark:text-white">
                      Checkout flow
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                        Passed
                      </span>
                      <span className="rounded-full bg-blue-500/15 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:text-blue-300">
                        Functional
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className="h-full w-4/5 rounded-full bg-gradient-to-r from-primary-500 to-cyan-500" />
                    </div>
                  </div>
                  <div className="space-y-4 rounded-2xl border border-dashed border-primary-500/30 bg-primary-500/5 p-5 dark:bg-primary-500/10">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Generating
                    </p>
                    <div className="space-y-2">
                      <div className="h-2.5 w-full animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
                      <div className="h-2.5 w-5/6 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
                      <div className="h-2.5 w-4/6 animate-pulse rounded-full bg-slate-200 dark:bg-slate-700" />
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      DOM-aware test case 4 of 5…
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="border-t border-slate-200/80 bg-white/50 py-20 dark:border-slate-800 dark:bg-[#080c14]/80">
          <div className="mx-auto max-w-6xl px-4 md:px-8">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="font-display text-3xl font-bold text-slate-900 dark:text-white md:text-4xl">
                Everything you need to explore UI quality
              </h2>
              <p className="mt-4 text-slate-600 dark:text-slate-400">
                Built for students, teams, and anyone who wants automation without writing every
                selector by hand.
              </p>
            </div>
            <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => {
                const FeatureIcon = feature.icon
                return (
                  <div
                    key={feature.title}
                    className="group rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm transition hover:border-primary-500/30 hover:shadow-md dark:border-slate-800 dark:bg-slate-900/50 dark:hover:border-primary-500/25"
                  >
                    <div className="mb-4 inline-flex rounded-xl bg-primary-600/10 p-3 text-primary-600 dark:bg-primary-500/15 dark:text-primary-400">
                      <FeatureIcon className="h-6 w-6" strokeWidth={1.75} />
                    </div>
                    <h3 className="font-display text-lg font-semibold text-slate-900 dark:text-white">
                      {feature.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      {feature.description}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* CTA band */}
        <section className="py-20">
          <div className="mx-auto max-w-6xl px-4 md:px-8">
            <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary-600 via-primary-700 to-violet-700 px-8 py-14 text-center shadow-2xl shadow-primary-900/20 md:px-16">
              <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
              <div className="pointer-events-none absolute -bottom-16 -left-16 h-48 w-48 rounded-full bg-cyan-400/20 blur-3xl" />
              <h2 className="relative font-display text-3xl font-bold text-white md:text-4xl">
                Ready to dive in?
              </h2>
              <p className="relative mx-auto mt-4 max-w-lg text-primary-100">
                Create an account, add a project URL, and let AQUA draft your first suite while you
                grab coffee.
              </p>
              <Link
                to="/login"
                className="relative mt-8 inline-flex items-center gap-2 rounded-2xl bg-white px-8 py-3.5 text-base font-semibold text-primary-700 shadow-lg transition hover:bg-primary-50"
              >
                Open the app
                <ArrowRight className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </section>

        <footer className="border-t border-slate-200/80 py-10 dark:border-slate-800">
          <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 text-center text-sm text-slate-500 md:flex-row md:px-8 md:text-left dark:text-slate-500">
            <div className="flex items-center gap-2">
              <img src={aquaLogo} alt="AQUA logo" className="h-8 w-auto object-contain" />
              <span className="font-display font-semibold text-slate-700 dark:text-slate-300">
                AQUA
              </span>
              <span className="hidden sm:inline">· Agentic QA</span>
            </div>
            <p>© {new Date().getFullYear()} AQUA. Built by group 14 for PBL-2.</p>
          </div>
        </footer>
      </main>
    </div>
  )
}
