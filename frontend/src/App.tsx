import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import DartPage from './pages/DartPage'
import StocksPage from './pages/StocksPage'
import PortfolioPage from './pages/PortfolioPage'
import SettingsPage from './pages/SettingsPage'
import { useWebSocket } from './hooks/useWebSocket'
import { useEffect } from 'react'
import { useAppStore } from './stores/appStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 30 * 1000, // 30초
    },
  },
})

function AppContent() {
  const { connect, disconnect, isConnected } = useWebSocket()
  const { setConnectionStatus } = useAppStore()

  useEffect(() => {
    // WebSocket 연결 임시 비활성화
    console.log('WebSocket 연결 비활성화됨')
    
    // 컴포넌트 언마운트 시 연결 해제
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  useEffect(() => {
    setConnectionStatus(isConnected)
  }, [isConnected, setConnectionStatus])

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/dart" element={<DartPage />} />
        <Route path="/stocks" element={<StocksPage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App