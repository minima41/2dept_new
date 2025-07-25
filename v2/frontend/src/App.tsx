import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import DartPage from './pages/DartPage'
import StockPage from './pages/StockPage'
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
  const setConnectionStatus = useAppStore(state => state.setConnectionStatus)

  useEffect(() => {
    // 백엔드 서버 준비 시간을 위한 약간의 지연
    const timer = setTimeout(() => {
      connect()
      console.log('WebSocket 연결 시도 중...')
    }, 500)
    
    // 컴포넌트 언마운트 시 연결 해제
    return () => {
      clearTimeout(timer)
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
        <Route path="/stocks" element={<StockPage />} />
        <Route path="/portfolio" element={<div className="p-6"><h1 className="text-2xl font-bold">포트폴리오 페이지</h1><p className="text-gray-600 mt-2">개발 예정</p></div>} />
        <Route path="/settings" element={<div className="p-6"><h1 className="text-2xl font-bold">설정 페이지</h1><p className="text-gray-600 mt-2">개발 예정</p></div>} />
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