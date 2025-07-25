import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAppStore, useAlerts, useConnectionStatus } from '../stores/appStore'
import { Button } from './ui/Button'
import { Badge } from './ui/Badge'
import { 
  Home, 
  FileText, 
  TrendingUp, 
  PieChart, 
  Settings, 
  Menu, 
  X, 
  Bell, 
  Wifi, 
  WifiOff,
  Activity
} from 'lucide-react'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: '대시보드', href: '/', icon: Home },
  { name: 'DART 공시', href: '/dart', icon: FileText },
  { name: '주가 모니터링', href: '/stocks', icon: TrendingUp },
  { name: '포트폴리오', href: '/portfolio', icon: PieChart },
  { name: '설정', href: '/settings', icon: Settings },
]

function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { sidebarOpen, toggleSidebar } = useAppStore()
  const { unreadCount } = useAlerts()
  const connectionStatus = useConnectionStatus()

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 사이드바 */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-16'} transition-all duration-300 bg-white shadow-lg flex flex-col border-r border-gray-200`}>
        {/* 로고 */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Activity className="h-5 w-5 text-white" />
            </div>
            {sidebarOpen && (
              <div className="ml-3">
                <h1 className="text-lg font-semibold text-gray-900">투자본부</h1>
                <p className="text-xs text-gray-500">모니터링 시스템</p>
              </div>
            )}
          </div>
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.href
            
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`w-full flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                {sidebarOpen && <span className="ml-3">{item.name}</span>}
              </Link>
            )
          })}
        </nav>

        {/* 연결 상태 */}
        <div className="p-4 border-t border-gray-200">
          <div className={`flex items-center ${sidebarOpen ? 'justify-between' : 'justify-center'}`}>
            <div className="flex items-center space-x-2">
              {connectionStatus === 'connected' ? (
                <Wifi className="h-4 w-4 text-green-500" />
              ) : (
                <WifiOff className="h-4 w-4 text-red-500" />
              )}
              {sidebarOpen && (
                <span className={`text-xs ${
                  connectionStatus === 'connected' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {connectionStatus === 'connected' ? '실시간 연결' : '연결 끊김'}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 헤더 */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
              >
                {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
              
              <div className="hidden sm:block">
                <h2 className="text-lg font-semibold text-gray-900">
                  {navigation.find(item => item.href === location.pathname)?.name || '대시보드'}
                </h2>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* 알림 */}
              <div className="relative">
                <Button variant="ghost" size="icon" className="relative">
                  <Bell className="h-5 w-5" />
                  {unreadCount > 0 && (
                    <Badge 
                      variant="danger" 
                      className="absolute -top-1 -right-1 h-5 w-5 rounded-full text-xs flex items-center justify-center p-0"
                    >
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </Badge>
                  )}
                </Button>
              </div>

              {/* 연결 상태 표시 */}
              <Badge 
                variant={connectionStatus === 'connected' ? 'success' : 'danger'}
                className="hidden sm:inline-flex"
              >
                {connectionStatus === 'connected' ? '실시간 연결' : '연결 끊김'}
              </Badge>
            </div>
          </div>
        </header>

        {/* 메인 콘텐츠 */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout