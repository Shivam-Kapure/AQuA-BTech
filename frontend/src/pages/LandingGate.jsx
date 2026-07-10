import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/useAuthStore'
import LandingPage from './LandingPage'

/**
 * Logged-in users skip marketing and go straight to the workspace.
 */
export default function LandingGate() {
  const token = useAuthStore((s) => s.token)
  if (token) return <Navigate to="/projects" replace />
  return <LandingPage />
}
