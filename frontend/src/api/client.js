import axios from 'axios'
import { useAuthStore } from '../store/useAuthStore'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const { token, routeJwt } = useAuthStore.getState()
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (routeJwt) config.headers['X-Aqua-Route-Jwt'] = routeJwt
  return config
})

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (
      err.response?.status === 401 &&
      err.config?.headers?.Authorization
    ) {
      useAuthStore.getState().clearSession()
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default client
