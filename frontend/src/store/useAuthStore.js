import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      user: null,
      routeJwt: '',
      setSession: (token, user) => set({ token, user }),
      clearSession: () => set({ token: null, user: null }),
      setRouteJwt: (routeJwt) => set({ routeJwt: routeJwt || '' }),
    }),
    { name: 'aqua-auth' }
  )
)
