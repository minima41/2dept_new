import { create } from 'zustand'
import { devtools, subscribeWithSelector } from 'zustand/middleware'

interface SystemStatus {
  service: string
  status: string
  message?: string
  timestamp?: string
}

interface Alert {
  id: string
  type: 'dart' | 'stock' | 'system'
  title: string
  message: string
  priority: 'high' | 'medium' | 'low'
  timestamp: string
  isRead: boolean
  data?: any
}

interface AppState {
  // 연결 상태
  isConnected: boolean
  connectionStatus: 'connected' | 'disconnected' | 'connecting'
  
  // 시스템 상태
  systemStatus: SystemStatus[]
  
  // 알림
  alerts: Alert[]
  unreadCount: number
  
  // UI 상태
  sidebarOpen: boolean
  
  // 실시간 데이터
  realtimeData: {
    dartUpdates: any[]
    stockUpdates: any[]
    lastUpdateTime: string | null
  }
  
  // 액션
  setConnectionStatus: (status: boolean) => void
  addSystemStatus: (status: SystemStatus) => void
  addAlert: (alert: Omit<Alert, 'id'>) => void
  markAlertAsRead: (id: string) => void
  removeAlert: (id: string) => void
  clearAlerts: () => void
  toggleSidebar: () => void
  addDartUpdate: (update: any) => void
  addStockUpdate: (update: any) => void
  setLastUpdateTime: (time: string) => void
}

export const useAppStore = create<AppState>()(
  devtools(
    subscribeWithSelector(
      (set) => ({
        // 초기 상태
        isConnected: false,
        connectionStatus: 'disconnected',
        systemStatus: [],
        alerts: [],
        unreadCount: 0,
        sidebarOpen: true,
        realtimeData: {
          dartUpdates: [],
          stockUpdates: [],
          lastUpdateTime: null,
        },
        
        // 액션
        setConnectionStatus: (status) => 
          set(() => ({
            isConnected: status,
            connectionStatus: status ? 'connected' : 'disconnected',
          })),
        
        addSystemStatus: (status) =>
          set((state) => ({
            systemStatus: [status, ...state.systemStatus.slice(0, 9)],
          })),
        
        addAlert: (alert) => 
          set((state) => {
            const newAlert: Alert = {
              ...alert,
              id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
            }
            
            return {
              alerts: [newAlert, ...state.alerts.slice(0, 99)],
              unreadCount: state.unreadCount + 1,
            }
          }),
        
        markAlertAsRead: (id) =>
          set((state) => {
            const alert = state.alerts.find(a => a.id === id)
            if (alert && !alert.isRead) {
              return {
                alerts: state.alerts.map(a => 
                  a.id === id ? { ...a, isRead: true } : a
                ),
                unreadCount: Math.max(0, state.unreadCount - 1),
              }
            }
            return state
          }),
        
        removeAlert: (id) =>
          set((state) => {
            const alert = state.alerts.find(a => a.id === id)
            return {
              alerts: state.alerts.filter(a => a.id !== id),
              unreadCount: alert && !alert.isRead ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
            }
          }),

        clearAlerts: () =>
          set(() => ({
            alerts: [],
            unreadCount: 0,
          })),
        
        toggleSidebar: () =>
          set((state) => ({
            sidebarOpen: !state.sidebarOpen,
          })),
        
        addDartUpdate: (update) =>
          set((state) => ({
            realtimeData: {
              ...state.realtimeData,
              dartUpdates: [update, ...state.realtimeData.dartUpdates.slice(0, 49)],
            },
          })),
        
        addStockUpdate: (update) =>
          set((state) => ({
            realtimeData: {
              ...state.realtimeData,
              stockUpdates: [update, ...state.realtimeData.stockUpdates.slice(0, 49)],
            },
          })),
        
        setLastUpdateTime: (time) =>
          set((state) => ({
            realtimeData: {
              ...state.realtimeData,
              lastUpdateTime: time,
            },
          })),
      })
    )
  )
)

// 선택자 함수들 - 메모화로 무한 리렌더링 방지
export const useConnectionStatus = () => useAppStore(state => state.connectionStatus)

export const useAlerts = () => {
  const alerts = useAppStore(state => state.alerts)
  const unreadCount = useAppStore(state => state.unreadCount)
  return { alerts, unreadCount }
}

export const useRealtimeData = () => useAppStore(state => state.realtimeData)