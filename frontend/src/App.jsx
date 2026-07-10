import { useEffect } from 'react'
import { BrowserRouter, Link, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/useAuthStore'
import { useThemeStore } from './store/useThemeStore'
import ThemeToggle from './components/ThemeToggle'
import LandingGate from './pages/LandingGate'
import LoginPage from './pages/LoginPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import { LogOut } from 'lucide-react'
import aquaLogo from './assets/aqua-logo.png'

function ProtectedLayout() {
  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const clearSession = useAuthStore((s) => s.clearSession)

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-md dark:border-slate-800 dark:bg-[#0b0f19]/90">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-4 py-3 md:px-8">
          <Link to="/projects" className="flex items-center gap-3 no-underline">
            <img src={aquaLogo} alt="AQUA logo" className="h-9 w-auto object-contain" />
            <div>
              <span className="font-display text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                AQUA
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400">Testing workspace</p>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            {user?.username ? (
              <span className="hidden text-sm text-slate-500 sm:inline dark:text-slate-400">
                {user.username}
              </span>
            ) : null}
            <ThemeToggle />
            <button
              type="button"
              onClick={() => {
                clearSession()
                window.location.href = '/login'
              }}
              className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-slate-200 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-4 py-6 md:px-8 md:py-8">
        <Outlet />
      </main>
    </div>
  )
}

function App() {
  const initTheme = useThemeStore((s) => s.initTheme)

  useEffect(() => {
    initTheme()
  }, [initTheme])

  return (
    <BrowserRouter>
      <Toaster position="top-center" toastOptions={{ className: 'dark:bg-slate-800 dark:text-white' }} />
      <Routes>
        <Route path="/" element={<LandingGate />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectName" element={<ProjectDetailPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
