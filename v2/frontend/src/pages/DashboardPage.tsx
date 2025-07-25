import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { useAppStore, useRealtimeData, useConnectionStatus } from '../stores/appStore'
import { api } from '../services/apiClient'
import { Activity, TrendingUp, TrendingDown, AlertCircle, DollarSign, BarChart3 } from 'lucide-react'

function DashboardPage() {
  const connectionStatus = useConnectionStatus()
  const realtimeData = useRealtimeData()

  // 통계 데이터 조회
  const { data: dartStats } = useQuery({
    queryKey: ['dart-statistics'],
    queryFn: api.dart.statistics,
    refetchInterval: 30000,
  })

  const { data: stockStats } = useQuery({
    queryKey: ['stock-statistics'],
    queryFn: api.stocks.statistics,
    refetchInterval: 30000,
  })

  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: api.system.status,
    refetchInterval: 30000,
  })

  const { data: monitoringStocks } = useQuery({
    queryKey: ['monitoring-stocks'],
    queryFn: api.stocks.monitoring,
    refetchInterval: 10000,
  })

  const handleForceCheck = async (type: 'dart' | 'stock') => {
    try {
      if (type === 'dart') {
        await api.dart.checkNow()
      } else {
        await api.stocks.checkNow()
      }
    } catch (error) {
      console.error('Manual check failed:', error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">대시보드</h1>
          <p className="text-gray-500 mt-1">투자본부 모니터링 시스템 V2</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={connectionStatus === 'connected' ? 'success' : 'danger'}>
            {connectionStatus === 'connected' ? '실시간 연결' : '연결 끊김'}
          </Badge>
          <Badge variant="primary">
            마지막 업데이트: {realtimeData.lastUpdateTime ? new Date(realtimeData.lastUpdateTime).toLocaleTimeString() : '없음'}
          </Badge>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">총 공시 건수</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{dartStats?.statistics?.total_disclosures || 0}</span>
              <Activity className="h-4 w-4 text-blue-500" />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              오늘 {dartStats?.statistics?.sent_alerts || 0}건 발송
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">모니터링 종목</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{stockStats?.statistics?.total_stocks || 0}</span>
              <BarChart3 className="h-4 w-4 text-green-500" />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              활성 알림 {stockStats?.statistics?.active_alerts || 0}건
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">포트폴리오 가치</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">
                {stockStats?.statistics?.total_portfolio_value 
                  ? `${(stockStats.statistics.total_portfolio_value / 100000000).toFixed(1)}억`
                  : '0원'
                }
              </span>
              <DollarSign className="h-4 w-4 text-yellow-500" />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {stockStats?.statistics?.total_profit_loss_rate 
                ? `${stockStats.statistics.total_profit_loss_rate > 0 ? '+' : ''}${stockStats.statistics.total_profit_loss_rate.toFixed(2)}%`
                : '0%'
              }
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">오늘 알림</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">
                {(dartStats?.statistics?.sent_alerts || 0) + (stockStats?.statistics?.today_alerts || 0)}
              </span>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              DART {dartStats?.statistics?.sent_alerts || 0} / 주가 {stockStats?.statistics?.today_alerts || 0}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 실시간 데이터 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 최근 DART 공시 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>최근 DART 공시</CardTitle>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleForceCheck('dart')}
              >
                수동 체크
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {realtimeData.dartUpdates.slice(0, 5).map((update, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm">{update.corp_name}</span>
                      <Badge variant="primary" className="text-xs">
                        {update.priority_score}점
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{update.report_nm}</p>
                    <div className="flex items-center space-x-2 mt-2">
                      {update.matched_keywords?.map((keyword: string, i: number) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {keyword}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <button 
                    onClick={() => window.open(update.dart_url, '_blank')}
                    className="text-blue-500 hover:text-blue-700 text-xs"
                  >
                    원문보기
                  </button>
                </div>
              ))}
              {realtimeData.dartUpdates.length === 0 && (
                <p className="text-gray-500 text-center py-4">최근 공시가 없습니다.</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 최근 주가 알림 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>최근 주가 알림</CardTitle>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleForceCheck('stock')}
              >
                수동 체크
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {realtimeData.stockUpdates.slice(0, 5).map((update, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm">{update.stock_name}</span>
                      <Badge 
                        variant={update.change_rate > 0 ? 'success' : update.change_rate < 0 ? 'danger' : 'secondary'}
                        className="text-xs"
                      >
                        {update.change_rate > 0 ? '+' : ''}{update.change_rate?.toFixed(2)}%
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {update.current_price?.toLocaleString()}원
                    </p>
                    {update.type === 'alert' && (
                      <p className="text-xs text-red-600 mt-1">{update.message}</p>
                    )}
                  </div>
                  <div className="text-right">
                    {update.change_rate > 0 ? (
                      <TrendingUp className="h-4 w-4 text-red-500" />
                    ) : update.change_rate < 0 ? (
                      <TrendingDown className="h-4 w-4 text-blue-500" />
                    ) : (
                      <Activity className="h-4 w-4 text-gray-500" />
                    )}
                  </div>
                </div>
              ))}
              {realtimeData.stockUpdates.length === 0 && (
                <p className="text-gray-500 text-center py-4">최근 주가 알림이 없습니다.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 시스템 상태 및 API 링크 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>시스템 상태</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium">백엔드 FastAPI</span>
                <Badge variant="success">정상</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium">프론트엔드 Vite</span>
                <Badge variant="success">정상</Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium">WebSocket 연결</span>
                <Badge variant={connectionStatus === 'connected' ? 'success' : 'danger'}>
                  {connectionStatus === 'connected' ? '연결됨' : '연결 끊김'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>빠른 액세스</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Button 
                variant="outline" 
                className="w-full justify-start"
                onClick={() => window.open('http://localhost:8000/docs', '_blank')}
              >
                📚 API 문서 (Swagger)
              </Button>
              <Button 
                variant="outline" 
                className="w-full justify-start"
                onClick={() => window.open('http://localhost:8000/api/system/status', '_blank')}
              >
                🔍 시스템 상태 조회
              </Button>
              <Button 
                variant="outline" 
                className="w-full justify-start"
                onClick={() => window.open('http://localhost:8000/api/system/diagnostics', '_blank')}
              >
                🛠️ 시스템 진단 정보
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DashboardPage