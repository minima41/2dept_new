import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Button } from './ui/Button'
import { Badge } from './ui/Badge'
import { useWebSocket } from '../hooks/useWebSocket'
import { api } from '../services/apiClient'
import { 
  Play, 
  Pause, 
  Trash2, 
  ArrowDown, 
  ArrowUp, 
  Filter, 
  Download,
  RefreshCw 
} from 'lucide-react'

interface LogMessage {
  timestamp: string
  level: string
  logger_name: string
  message: string
  module: string
  function: string
  line_number: number
  thread_id: number
  process_id: number
  exception?: string
  pathname: string
  filename: string
}

type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'ALL'

function LogViewer() {
  const [logs, setLogs] = useState<LogMessage[]>([])
  const [filteredLogs, setFilteredLogs] = useState<LogMessage[]>([])
  const [selectedLevel, setSelectedLevel] = useState<LogLevel>('ALL')
  const [isAutoScroll, setIsAutoScroll] = useState(true)
  const [isPaused, setIsPaused] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [maxLogCount] = useState(500)
  
  const logContainerRef = useRef<HTMLDivElement>(null)
  const { socket, isWebSocketConnected } = useWebSocket()

  // WebSocket 연결 상태 업데이트
  useEffect(() => {
    setIsConnected(isWebSocketConnected)
  }, [isWebSocketConnected])

  // 초기 로그 로드
  useEffect(() => {
    loadRecentLogs()
  }, [])

  // WebSocket 메시지 수신
  useEffect(() => {
    if (!socket) return

    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data)
        if (message.type === 'log_message' && !isPaused) {
          const logMessage: LogMessage = message.data
          addLogMessage(logMessage)
        }
      } catch (error) {
        console.error('WebSocket 메시지 파싱 오류:', error)
      }
    }

    socket.addEventListener('message', handleMessage)
    return () => socket.removeEventListener('message', handleMessage)
  }, [socket, isPaused])

  // 로그 필터링
  useEffect(() => {
    if (selectedLevel === 'ALL') {
      setFilteredLogs(logs)
    } else {
      setFilteredLogs(logs.filter(log => log.level === selectedLevel))
    }
  }, [logs, selectedLevel])

  // 자동 스크롤
  useEffect(() => {
    if (isAutoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [filteredLogs, isAutoScroll])

  const loadRecentLogs = async () => {
    try {
      const response = await api.logs.recent(100)
      setLogs(response.logs || [])
    } catch (error) {
      console.error('최근 로그 로드 실패:', error)
    }
  }

  const addLogMessage = (logMessage: LogMessage) => {
    setLogs(prevLogs => {
      const newLogs = [...prevLogs, logMessage]
      // 최대 로그 수 제한
      if (newLogs.length > maxLogCount) {
        return newLogs.slice(-maxLogCount)
      }
      return newLogs
    })
  }

  const clearLogs = async () => {
    try {
      await api.logs.clear()
      setLogs([])
    } catch (error) {
      console.error('로그 클리어 실패:', error)
    }
  }

  const generateTestLog = async (level: string) => {
    try {
      await api.logs.test(level, `테스트 ${level} 로그 메시지 - ${new Date().toLocaleTimeString()}`)
    } catch (error) {
      console.error('테스트 로그 생성 실패:', error)
    }
  }

  const downloadLogs = () => {
    const logText = filteredLogs.map(log => 
      `[${log.timestamp}] ${log.level} - ${log.logger_name} - ${log.message}${log.exception ? `\n${log.exception}` : ''}`
    ).join('\n')
    
    const blob = new Blob([logText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs_${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }


  const getLogLevelBadgeVariant = (level: string) => {
    switch (level) {
      case 'DEBUG': return 'secondary' as const
      case 'INFO': return 'primary' as const
      case 'WARNING': return 'warning' as const
      case 'ERROR': return 'danger' as const
      default: return 'secondary' as const
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ko-KR', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <div className="p-6 space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">실시간 로그</h1>
          <p className="text-gray-500 mt-1">
            시스템 로그를 실시간으로 모니터링하세요
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={isConnected ? 'success' : 'danger'} className="text-xs">
            {isConnected ? '연결됨' : '연결 끊김'}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            {filteredLogs.length}개 로그
          </Badge>
        </div>
      </div>

      {/* 컨트롤 패널 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {/* 로그 레벨 필터 */}
              <div className="flex items-center space-x-2">
                <Filter className="h-4 w-4 text-gray-500" />
                <span className="text-sm font-medium">레벨:</span>
                <select
                  value={selectedLevel}
                  onChange={(e) => setSelectedLevel(e.target.value as LogLevel)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="ALL">전체</option>
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
              </div>

              {/* 자동 스크롤 토글 */}
              <Button
                variant={isAutoScroll ? 'default' : 'outline'}
                size="sm"
                onClick={() => setIsAutoScroll(!isAutoScroll)}
              >
                {isAutoScroll ? <ArrowDown className="h-4 w-4 mr-1" /> : <ArrowUp className="h-4 w-4 mr-1" />}
                자동스크롤
              </Button>

              {/* 일시정지 토글 */}
              <Button
                variant={isPaused ? 'default' : 'outline'}
                size="sm"
                onClick={() => setIsPaused(!isPaused)}
              >
                {isPaused ? <Play className="h-4 w-4 mr-1" /> : <Pause className="h-4 w-4 mr-1" />}
                {isPaused ? '재시작' : '일시정지'}
              </Button>
            </div>

            <div className="flex items-center space-x-2">
              {/* 테스트 로그 생성 */}
              <div className="flex items-center space-x-1">
                <span className="text-sm text-gray-500">테스트:</span>
                <Button size="sm" variant="outline" onClick={() => generateTestLog('debug')}>
                  DEBUG
                </Button>
                <Button size="sm" variant="outline" onClick={() => generateTestLog('info')}>
                  INFO
                </Button>
                <Button size="sm" variant="outline" onClick={() => generateTestLog('warning')}>
                  WARN
                </Button>
                <Button size="sm" variant="outline" onClick={() => generateTestLog('error')}>
                  ERROR
                </Button>
              </div>

              {/* 기능 버튼들 */}
              <Button size="sm" variant="outline" onClick={loadRecentLogs}>
                <RefreshCw className="h-4 w-4 mr-1" />
                새로고침
              </Button>
              <Button size="sm" variant="outline" onClick={downloadLogs}>
                <Download className="h-4 w-4 mr-1" />
                다운로드
              </Button>
              <Button size="sm" variant="outline" onClick={clearLogs}>
                <Trash2 className="h-4 w-4 mr-1" />
                클리어
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 로그 표시 영역 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>로그 메시지</span>
            <span className="text-sm font-normal text-gray-500">
              {selectedLevel === 'ALL' ? '전체' : selectedLevel} 레벨 ({filteredLogs.length}개)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            ref={logContainerRef}
            className="h-96 overflow-y-auto bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm"
            style={{ fontFamily: 'Consolas, Monaco, "Courier New", monospace' }}
          >
            {filteredLogs.length === 0 ? (
              <div className="text-center text-gray-400 py-8">
                표시할 로그가 없습니다.
              </div>
            ) : (
              filteredLogs.map((log, index) => (
                <div key={index} className="mb-2 border-b border-gray-700 pb-2">
                  <div className="flex items-start space-x-2">
                    <span className="text-gray-400 text-xs min-w-[80px]">
                      {formatTime(log.timestamp)}
                    </span>
                    <Badge 
                      variant={getLogLevelBadgeVariant(log.level)}
                      className="text-xs min-w-[60px] text-center"
                    >
                      {log.level}
                    </Badge>
                    <span className="text-blue-300 text-xs min-w-[120px] truncate">
                      {log.logger_name}
                    </span>
                    <span className="flex-1 text-white">
                      {log.message}
                    </span>
                  </div>
                  
                  {/* 상세 정보 (마우스 오버 시 표시할 수 있음) */}
                  <div className="text-xs text-gray-500 mt-1">
                    {log.filename}:{log.line_number} in {log.function}()
                  </div>
                  
                  {/* 예외 정보 */}
                  {log.exception && (
                    <div className="text-red-300 text-xs mt-1 whitespace-pre-wrap">
                      {log.exception}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default LogViewer