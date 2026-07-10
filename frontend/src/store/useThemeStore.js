import { create } from 'zustand'
import { persist } from 'zustand/middleware'

function applyMode(mode) {
  const root = document.documentElement
  if (mode === 'dark') {
    root.classList.add('dark')
    root.classList.remove('light')
  } else {
    root.classList.add('light')
    root.classList.remove('dark')
  }
}

export const useThemeStore = create(
  persist(
    (set, get) => ({
      mode: 'dark',
      setMode: (mode) => {
        set({ mode })
        applyMode(mode)
      },
      toggle: () => {
        const next = get().mode === 'dark' ? 'light' : 'dark'
        get().setMode(next)
      },
      initTheme: () => applyMode(get().mode),
    }),
    {
      name: 'aqua-theme',
      onRehydrateStorage: () => (state) => {
        if (state?.mode) applyMode(state.mode)
      },
    }
  )
)
