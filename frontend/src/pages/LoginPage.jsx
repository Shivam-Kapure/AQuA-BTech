import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import client from '../api/client'
import ThemeToggle from '../components/ThemeToggle'
import { useAuthStore } from '../store/useAuthStore'
import aquaLogo from '../assets/aqua-logo.png'

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const token = useAuthStore((s) => s.token)
  const setSession = useAuthStore((s) => s.setSession)
  const navigate = useNavigate()

  useEffect(() => {
    if (token) navigate('/projects', { replace: true })
  }, [token, navigate])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const path = mode === 'login' ? '/api/v1/auth/login' : '/api/v1/auth/register'
      const { data } = await client.post(path, { username, password })
      setSession(data.access_token, data.user)
      toast.success(mode === 'login' ? 'Welcome back' : 'Account created')
      navigate('/projects', { replace: true })
    } catch (err) {
      const d = err.response?.data?.detail
      toast.error(typeof d === 'string' ? d : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-16">
      <div className="absolute left-4 top-4 flex items-center gap-3 md:left-8 md:top-8">
        <Link
          to="/"
          className="text-sm font-medium text-slate-500 transition hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400"
        >
          ← Home
        </Link>
      </div>
      <div className="absolute right-4 top-4 md:right-8 md:top-8">
        <ThemeToggle />
      </div>
      <div className="mb-10 text-center">
        <img src={aquaLogo} alt="AQUA logo" className="mx-auto mb-4 h-14 w-auto object-contain" />
        <h1 className="font-display text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
          AQUA
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">Agentic QA & automated UI testing</p>
      </div>

      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-xl dark:border-slate-700 dark:bg-[#12151c]">
        <div className="mb-6 flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
          <button
            type="button"
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
              mode === 'login'
                ? 'bg-white text-slate-900 shadow dark:bg-slate-900 dark:text-white'
                : 'text-slate-500 dark:text-slate-400'
            }`}
            onClick={() => setMode('login')}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
              mode === 'register'
                ? 'bg-white text-slate-900 shadow dark:bg-slate-900 dark:text-white'
                : 'text-slate-500 dark:text-slate-400'
            }`}
            onClick={() => setMode('register')}
          >
            Register
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Username
            </span>
            <input
              autoComplete="username"
              required
              minLength={2}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-slate-900 outline-none ring-primary-500/30 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Password
            </span>
            <input
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
              minLength={6}
              className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-slate-900 outline-none ring-primary-500/30 focus:ring-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button type="submit" disabled={busy} className="btn-primary mt-2 w-full py-3">
            {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
          By continuing you agree to use this demo environment responsibly.
        </p>
      </div>
    </div>
  )
}
