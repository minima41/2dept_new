import { useCallback, useEffect, useRef, useState } from 'react'
import { useAppStore } from '../stores/appStore'

const WS_URL = 'ws://localhost:8000/ws'

interface WebSocketMessage {
  type: string
  data?: any
  timestamp?: string
  message?: string
  client_id?: string
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

  // Zustand store actions 한 번만 가져오기
  const addAlert = useAppStore(state => state.addAlert)
  const addSystemStatus = useAppStore(state => state.addSystemStatus)  
  const addDartUpdate = useAppStore(state => state.addDartUpdate)
  const addStockUpdate = useAppStore(state => state.addStockUpdate)
  const setLastUpdateTime = useAppStore(state => state.setLastUpdateTime)

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      console.log('WebSocket message received:', message)
      
      setLastUpdateTime(new Date().toISOString())
      
      switch (message.type) {
        case 'connection':
          console.log('WebSocket connection confirmed:', message.message, 'Client ID:', message.client_id)
          break
          
        case 'connection_status':
          console.log('Connection status:', message.data)
          break
          
        case 'heartbeat':
          // 하트비트는 조용히 처리
          break
          
        case 'dart_statistics':
          // DART 통계 데이터는 React Query가 처리하므로 로그만 남김
          console.log('DART statistics received:', message.data)
          break
          
        case 'stock_statistics':
          // 주식 통계 데이터는 React Query가 처리하므로 로그만 남김
          console.log('Stock statistics received:', message.data)
          break
          
        case 'stock_list':
          // 주식 목록 데이터는 React Query가 처리하므로 로그만 남김
          console.log('Stock list received:', message.data)
          break
          
        case 'dart_update':
          if (message.data) {
            addDartUpdate(message.data)
            
            addAlert({
              type: 'dart',
              title: `[DART] ${message.data.corp_name}`,
              message: message.data.report_nm,
              priority: message.data.priority_score > 80 ? 'high' : 'medium',
              timestamp: message.timestamp || new Date().toISOString(),
              isRead: false,
              data: message.data
            })
          }
          break
          
        case 'stock_update':
          if (message.data) {
            addStockUpdate(message.data)
            
            if (message.data.type === 'alert') {
              addAlert({
                type: 'stock',
                title: `[주가] ${message.data.stock_name}`,
                message: message.data.message,
                priority: 'high',
                timestamp: message.timestamp || new Date().toISOString(),
                isRead: false,
                data: message.data
              })
            }
          }
          break
          
        case 'system_status':
          if (message.data) {
            addSystemStatus({
              service: message.data.service || 'system',
              status: message.data.status || 'info',
              message: message.data.message,
              timestamp: message.timestamp || new Date().toISOString()
            })
          }
          break
          
        default:
          console.log('Unknown message type:', message.type, message.data)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error, event.data)
    }
  }, [addAlert, addSystemStatus, addDartUpdate, addStockUpdate, setLastUpdateTime])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket is already connected')
      return
    }

    try {
      setConnectionStatus('connecting')
      wsRef.current = new WebSocket(WS_URL)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setConnectionStatus('connected')
        reconnectAttempts.current = 0
      }

      wsRef.current.onmessage = handleMessage

      wsRef.current.onerror = (error) => {
        console.log('WebSocket error:', error)
        setConnectionStatus('error')
      }

      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setIsConnected(false)
        setConnectionStatus('disconnected')

        // 자동 재연결 (정상 종료가 아닌 경우)
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000)
          console.log(`Attempting to reconnect in ${delay}ms...`)
          
          reconnectTimeoutRef.current = window.setTimeout(() => {
            reconnectAttempts.current++
            connect()
          }, delay)
        }
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionStatus('error')
    }
  }, [handleMessage])

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
      console.warn('WebSocket is not connected. Message not sent:', message)
    }
  }, [])

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    isConnected,
    connect,
    disconnect,
    sendMessage,
    connectionStatus,
  }
}