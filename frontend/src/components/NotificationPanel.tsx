import { useEffect } from 'react'
import { useAlerts, useAlertActions } from '../stores/appStore'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { X } from 'lucide-react'

function NotificationPanel() {
  const { alerts, unreadCount } = useAlerts()
  const { removeAlert, clearAlerts } = useAlertActions()

  // 자동 삭제 타이머 설정
  useEffect(() => {
    const timers: number[] = []

    alerts.forEach(alert => {
      // 우선순위가 'low'인 알림은 5초 후 자동 삭제
      // 'medium'은 10초, 'high'는 자동 삭제하지 않음
      let autoRemoveDelay = 0
      
      if (alert.priority === 'low') {
        autoRemoveDelay = 5000 // 5초
      } else if (alert.priority === 'medium') {
        autoRemoveDelay = 10000 // 10초
      }
      // high priority는 자동 삭제하지 않음

      if (autoRemoveDelay > 0) {
        // 알림이 생성된 시점부터 계산
        const alertAge = Date.now() - new Date(alert.timestamp).getTime()
        const remainingTime = Math.max(0, autoRemoveDelay - alertAge)
        
        if (remainingTime > 0) {
          const timer = window.setTimeout(() => {
            removeAlert(alert.id)
          }, remainingTime)
          
          timers.push(timer)
        } else {
          // 이미 시간이 지났으면 즉시 삭제
          removeAlert(alert.id)
        }
      }
    })

    // 클린업
    return () => {
      timers.forEach(timer => window.clearTimeout(timer))
    }
  }, [alerts, removeAlert])

  if (alerts.length === 0) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-40 w-80 max-h-96 overflow-y-auto bg-white rounded-lg shadow-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-900">실시간 알림</h3>
          <div className="flex items-center space-x-2">
            <Badge variant="primary" className="text-xs">
              {unreadCount}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAlerts}
              className="text-xs px-2 py-1"
            >
              모두 지우기
            </Button>
          </div>
        </div>
      </div>
      <div className="max-h-80 overflow-y-auto">
        {alerts.slice(0, 10).map((alert) => (
          <div
            key={alert.id}
            className={`p-3 border-b border-gray-100 relative group ${
              !alert.isRead ? 'bg-blue-50' : 'bg-white'
            }`}
          >
            <div className="flex items-start space-x-3">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <h4 className="text-sm font-medium text-gray-900">{alert.title}</h4>
                  <Badge 
                    variant={alert.priority === 'high' ? 'danger' : alert.priority === 'medium' ? 'warning' : 'secondary'}
                    className="text-xs"
                  >
                    {alert.priority}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                <div className="flex items-center justify-between mt-1">
                  <p className="text-xs text-gray-400">
                    {new Date(alert.timestamp).toLocaleTimeString('ko-KR')}
                  </p>
                  {alert.priority === 'low' && (
                    <p className="text-xs text-gray-400">5초 후 자동 삭제</p>
                  )}
                  {alert.priority === 'medium' && (
                    <p className="text-xs text-gray-400">10초 후 자동 삭제</p>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeAlert(alert.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 h-6 w-6"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default NotificationPanel