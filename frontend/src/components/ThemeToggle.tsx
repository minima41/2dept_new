import { useState } from 'react'
import { useTheme, Theme } from '../contexts/ThemeContext'
import { Button } from './ui/Button'
import { Sun, Moon, Palette, ChevronDown } from 'lucide-react'

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)

  const themes: { value: Theme; label: string; icon: React.ComponentType<any>; description: string }[] = [
    {
      value: 'light',
      label: '라이트',
      icon: Sun,
      description: '밝은 테마'
    },
    {
      value: 'dark',
      label: '다크',
      icon: Moon,
      description: '어두운 테마'
    },
    {
      value: 'prompt',
      label: '프롬프트',
      icon: Palette,
      description: '터미널 스타일'
    }
  ]

  const currentTheme = themes.find(t => t.value === theme)
  const CurrentIcon = currentTheme?.icon || Sun

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      {/* 테마 토글 버튼 */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2"
      >
        <CurrentIcon className="h-4 w-4" />
        <span className="hidden sm:inline text-sm">{currentTheme?.label}</span>
        <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </Button>

      {/* 드롭다운 메뉴 */}
      {isOpen && (
        <>
          {/* 오버레이 */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* 메뉴 */}
          <div className="absolute right-0 top-full mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20">
            <div className="p-2">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 px-2 py-1 mb-1">
                테마 선택
              </div>
              
              {themes.map((themeOption) => {
                const Icon = themeOption.icon
                const isSelected = theme === themeOption.value
                
                return (
                  <button
                    key={themeOption.value}
                    onClick={() => handleThemeChange(themeOption.value)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm transition-colors ${
                      isSelected
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${
                      isSelected 
                        ? 'text-blue-600 dark:text-blue-400' 
                        : 'text-gray-500 dark:text-gray-400'
                    }`} />
                    <div className="flex-1 text-left">
                      <div className="font-medium">{themeOption.label}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {themeOption.description}
                      </div>
                    </div>
                    {isSelected && (
                      <div className="w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full" />
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ThemeToggle