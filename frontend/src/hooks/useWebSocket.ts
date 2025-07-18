import { useCallback, useEffect, useRef, useState } from 'react'
import { useAppStore } from '../stores/appStore'

const WS_URL = (import.meta as any).env.VITE_WS_URL || 'ws://localhost:8000'

interface WebSocketMessage {
  type: string
  data?: any
  timestamp?: string
}

interface UseWebSocketReturn {
  isConnected: boolean
  connect: () => void
  disconnect: () => void
  sendMessage: (message: any) => void
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
}

export const useWebSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<UseWebSocketReturn['connectionStatus']>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  const {
    addAlert,
    addSystemStatus,
    addDartUpdate,
    addStockUpdate,
    setLastUpdateTime,
  } = useAppStore()

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      
      // 마지막 업데이트 시간 설정
      setLastUpdateTime(new Date().toISOString())
      
      switch (message.type) {
        case 'dart_update':
          if (message.data) {
            addDartUpdate(message.data)
            
            // 알림 생성
            addAlert({
              type: 'dart',
              title: `[DART] ${message.data.corp_name}`,
              message: message.data.report_nm,
              priority: message.data.priority_score >= 3 ? 'high' : 'medium',
              timestamp: new Date().toISOString(),
              isRead: false,
              data: message.data,
            })
          }
          break
          
        case 'stock_update':
          if (message.data) {
            addStockUpdate(message.data)
            
            // 알림 타입에 따라 알림 생성
            if (message.data.type === 'alert') {
              const alertType = message.data.alert_type
              const priority = ['take_profit', 'stop_loss'].includes(alertType) ? 'high' : 'medium'
              
              addAlert({
                type: 'stock',
                title: `[주가] ${message.data.stock_name}`,
                message: message.data.message,
                priority,
                timestamp: new Date().toISOString(),
                isRead: false,
                data: message.data,
              })
            }
          }
          break
          
        case 'system_status':
          if (message.data) {
            addSystemStatus({
              service: message.data.service,
              status: message.data.status,
              message: message.data.message,
              timestamp: new Date().toISOString(),
            })
            
            // 중요한 시스템 상태 변경 시 알림
            if (['error', 'stopped'].includes(message.data.status)) {
              addAlert({
                type: 'system',
                title: `[시스템] ${message.data.service}`,
                message: message.data.message || '시스템 상태가 변경되었습니다.',
                priority: 'high',
                timestamp: new Date().toISOString(),
                isRead: false,
                data: message.data,
              })
            }
          }
          break
          
        case 'alert_triggered':
          if (message.data) {
            addAlert({
              type: message.data.alert_type === 'dart' ? 'dart' : 'stock',
              title: message.data.title,
              message: message.data.message,
              priority: 'high',
              timestamp: new Date().toISOString(),
              isRead: false,
              data: message.data,
            })
          }
          break
          
        case 'user_connected':
          console.log('WebSocket connected:', message.data)
          break
          
        case 'ping':
          // 서버에서 온 ping에 대해 pong 응답
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong' }))
          }
          break
          
        case 'error':
          console.error('WebSocket error:', message.data)
          addAlert({
            type: 'system',
            title: '[시스템] WebSocket 오류',
            message: message.data?.error || 'WebSocket 연결에 오류가 발생했습니다.',
            priority: 'high',
            timestamp: new Date().toISOString(),
            isRead: false,
            data: message.data,
          })
          break
          
        default:
          console.log('Unknown message type:', message.type, message.data)
      }
    } catch (error) {
      console.error('WebSocket message parsing error:', error)
    }
  }, [addAlert, addSystemStatus, addDartUpdate, addStockUpdate, setLastUpdateTime])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket is already connected')
      return
    }

    try {
      setConnectionStatus('connecting')
      
      const ws = new WebSocket(`${WS_URL}/ws`)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setConnectionStatus('connected')
        reconnectAttempts.current = 0
        
        // 연결 성공 알림
        addAlert({
          type: 'system',
          title: '[시스템] 연결 성공',
          message: '실시간 모니터링이 시작되었습니다.',
          priority: 'low',
          timestamp: new Date().toISOString(),
          isRead: false,
        })
      }
      
      ws.onmessage = handleMessage
      
      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setIsConnected(false)
        setConnectionStatus('disconnected')
        wsRef.current = null
        
        // 의도적인 종료가 아닌 경우 재연결 시도
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          console.log(`Attempting to reconnect in ${delay}ms...`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++
            connect()
          }, delay)
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          addAlert({
            type: 'system',
            title: '[시스템] 연결 실패',
            message: '서버와의 연결이 중단되었습니다. 페이지를 새로고침 해주세요.',
            priority: 'high',
            timestamp: new Date().toISOString(),
            isRead: false,
          })
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus('error')
        
        addAlert({
          type: 'system',
          title: '[시스템] 연결 오류',
          message: '서버와의 연결에 문제가 발생했습니다.',
          priority: 'high',
          timestamp: new Date().toISOString(),
          isRead: false,
        })
      }
      
      wsRef.current = ws
      
    } catch (error) {
      console.error('WebSocket connection error:', error)
      setConnectionStatus('error')
    }
  }, [handleMessage, addAlert])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    
    setIsConnected(false)
    setConnectionStatus('disconnected')
    reconnectAttempts.current = 0
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  // 페이지 가시성 변경 시 재연결
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // 페이지가 숨겨질 때는 연결 유지
        return
      } else {
        // 페이지가 다시 보일 때 연결 상태 확인
        if (!isConnected && wsRef.current?.readyState !== WebSocket.CONNECTING) {
          connect()
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [isConnected, connect])

  return {
    isConnected,
    connect,
    disconnect,
    sendMessage,
    connectionStatus,
  }
}