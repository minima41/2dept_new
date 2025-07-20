import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

export type Theme = 'light' | 'dark' | 'prompt'

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  isDark: boolean
  isPrompt: boolean
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

interface ThemeProviderProps {
  children: ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>('light')

  // 시스템 다크모드 감지
  const getSystemTheme = (): 'light' | 'dark' => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'light'
  }

  // 초기 테마 설정 (시스템 테마 기반)
  useEffect(() => {
    const systemTheme = getSystemTheme()
    setTheme(systemTheme)
  }, [])

  // 테마 변경 시 HTML 클래스 업데이트
  useEffect(() => {
    const root = window.document.documentElement
    
    // 기존 테마 클래스 제거
    root.classList.remove('light', 'dark', 'prompt')
    
    // 새로운 테마 클래스 추가
    root.classList.add(theme)
    
    // 다크모드 클래스 처리 (TailwindCSS용)
    if (theme === 'dark' || theme === 'prompt') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [theme])

  // 시스템 테마 변경 감지
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = (e: MediaQueryListEvent) => {
      // 현재 테마가 light나 dark인 경우에만 시스템 테마에 따라 변경
      if (theme === 'light' || theme === 'dark') {
        setTheme(e.matches ? 'dark' : 'light')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  const contextValue: ThemeContextType = {
    theme,
    setTheme,
    isDark: theme === 'dark',
    isPrompt: theme === 'prompt'
  }

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}