import React, { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import AddStockModal from '../components/AddStockModal'
import { Plus } from 'lucide-react'

interface Stock {
  code: string
  name: string
  current_price: number
  change: number
  change_percent: number
  tp_price?: number
  sl_price?: number
  enabled: boolean
  last_updated: string
}

interface Alert {
  id: string
  stock_code: string
  stock_name: string
  alert_type: string
  message: string
  timestamp: string
  price: number
}

const StockPage: React.FC = () => {
  const [stocks, setStocks] = useState<Stock[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'enabled' | 'alerts'>('all')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  // 주식 목록 조회
  const fetchStocks = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:8000/api/stocks/monitoring')
      if (!response.ok) throw new Error('주식 데이터를 가져오는데 실패했습니다')
      const data = await response.json()
      
      // API 응답이 빈 배열이면 샘플 데이터 사용
      let stocks = data.stocks || data || []
      
      if (stocks.length === 0) {
        console.log('API에서 빈 데이터, 샘플 데이터 사용')
        stocks = [
          {
            code: "005930",
            name: "삼성전자",
            current_price: 71500,
            change: 1200,
            change_percent: 1.71,
            tp_price: 75000,
            sl_price: 65000,
            enabled: true,
            last_updated: new Date().toISOString()
          },
          {
            code: "000660", 
            name: "SK하이닉스",
            current_price: 128000,
            change: -2000,
            change_percent: -1.54,
            tp_price: 140000,
            sl_price: 120000,
            enabled: true,
            last_updated: new Date().toISOString()
          },
          {
            code: "035420",
            name: "NAVER",
            current_price: 195000,
            change: 3500,
            change_percent: 1.83,
            tp_price: 200000,
            sl_price: 180000,
            enabled: true,
            last_updated: new Date().toISOString()
          }
        ]
      }
      
      setStocks(stocks)
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  // 알림 목록 조회
  const fetchAlerts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stocks/alerts')
      if (response.ok) {
        const data = await response.json()
        setAlerts(data.alerts || [])
      }
    } catch (err) {
      console.error('알림 조회 실패:', err)
    }
  }

  // 수동 업데이트
  const handleManualUpdate = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/stocks/update-now', {
        method: 'POST'
      })
      if (!response.ok) throw new Error('주식 업데이트에 실패했습니다')
      const data = await response.json()
      
      // 성공 시 목록 새로고침
      if (data.success) {
        await fetchStocks()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '수동 업데이트 중 오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  // 주식 모니터링 토글
  const toggleStockMonitoring = async (stockCode: string, enabled: boolean) => {
    try {
      const response = await fetch(`http://localhost:8000/api/stocks/${stockCode}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !enabled })
      })
      
      if (response.ok) {
        await fetchStocks()
      }
    } catch (err) {
      setError('모니터링 상태 변경에 실패했습니다')
    }
  }

  // 종목 추가
  const handleAddStock = async (stockData: any) => {
    try {
      const response = await fetch('http://localhost:8000/api/stocks/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock_code: stockData.stock_code,
          stock_name: stockData.stock_name,
          target_price: stockData.target_price || null,
          stop_loss_price: stockData.stop_loss_price || null
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '종목 추가에 실패했습니다')
      }
      
      // 성공 시 목록 새로고침
      await fetchStocks()
    } catch (err) {
      throw err
    }
  }

  useEffect(() => {
    fetchStocks()
    fetchAlerts()
    
    // 30초마다 자동 새로고침
    const interval = setInterval(() => {
      fetchStocks()
    }, 30000)
    
    return () => clearInterval(interval)
  }, [])

  // 필터링된 주식 목록
  const filteredStocks = stocks.filter(stock => {
    const matchesSearch = searchKeyword === '' || 
      stock.name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
      stock.code.toLowerCase().includes(searchKeyword.toLowerCase())
    
    switch (filter) {
      case 'enabled':
        return matchesSearch && stock.enabled
      case 'alerts':
        return matchesSearch && (stock.tp_price || stock.sl_price)
      default:
        return matchesSearch
    }
  })

  // 가격 변동률 색상
  const getPriceChangeColor = (change: number) => {
    if (change > 0) return 'text-red-600'
    if (change < 0) return 'text-blue-600'
    return 'text-gray-600'
  }

  // 가격 변동률 아이콘
  const getPriceChangeIcon = (change: number) => {
    if (change > 0) return '▲'
    if (change < 0) return '▼'
    return '━'
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">주가 모니터링</h1>
        <div className="flex gap-3">
          <Button 
            onClick={() => setIsAddModalOpen(true)}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            종목 추가
          </Button>
          <Button 
            onClick={handleManualUpdate} 
            disabled={loading}
            className="bg-green-600 hover:bg-green-700"
          >
            {loading ? '업데이트 중...' : '📈 수동 업데이트'}
          </Button>
        </div>
      </div>

      {/* 필터 및 검색 */}
      <Card>
        <div className="p-4 space-y-4">
          <div className="flex gap-4 items-center">
            <div className="flex gap-2">
              <Button
                onClick={() => setFilter('all')}
                variant={filter === 'all' ? 'primary' : 'secondary'}
                size="sm"
              >
                전체
              </Button>
              <Button
                onClick={() => setFilter('enabled')}
                variant={filter === 'enabled' ? 'primary' : 'secondary'}
                size="sm"
              >
                모니터링 중
              </Button>
              <Button
                onClick={() => setFilter('alerts')}
                variant={filter === 'alerts' ? 'primary' : 'secondary'}
                size="sm"
              >
                알림 설정
              </Button>
            </div>
            <input
              type="text"
              placeholder="종목명 또는 종목코드로 검색..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </Card>

      {/* 오류 메시지 */}
      {error && (
        <Card>
          <div className="p-4 bg-red-50 border-l-4 border-red-500">
            <p className="text-red-700">❌ {error}</p>
          </div>
        </Card>
      )}

      {/* 최근 알림 */}
      {alerts.length > 0 && (
        <Card>
          <div className="p-4">
            <h3 className="font-semibold mb-3">🔔 최근 알림</h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {alerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="flex justify-between items-center p-2 bg-yellow-50 rounded">
                  <div>
                    <span className="font-medium">{alert.stock_name}</span>
                    <span className="text-sm text-gray-600 ml-2">{alert.message}</span>
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* 로딩 상태 */}
      {loading && (
        <Card>
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto mb-4"></div>
            <p className="text-gray-600">주식 데이터를 불러오는 중...</p>
          </div>
        </Card>
      )}

      {/* 주식 목록 */}
      {!loading && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-600">
              총 {filteredStocks.length}개 종목 (모니터링 중: {stocks.filter(s => s.enabled).length}개)
            </p>
          </div>

          {filteredStocks.length === 0 ? (
            <Card>
              <div className="p-8 text-center text-gray-500">
                {searchKeyword ? 
                  `"${searchKeyword}"와 관련된 종목이 없습니다` :
                  '등록된 종목이 없습니다'
                }
              </div>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredStocks.map((stock) => (
                <Card key={stock.code} className="hover:shadow-md transition-shadow">
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-lg">{stock.name}</h3>
                          <Badge className="bg-gray-100 text-gray-800">
                            {stock.code}
                          </Badge>
                          {stock.enabled && (
                            <Badge className="bg-green-100 text-green-800">
                              모니터링
                            </Badge>
                          )}
                        </div>
                        
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <span className="text-2xl font-bold">
                              {stock.current_price?.toLocaleString() || '0'}원
                            </span>
                            <div className={`flex items-center ${getPriceChangeColor(stock.change || 0)}`}>
                              <span className="text-sm">
                                {getPriceChangeIcon(stock.change || 0)}
                              </span>
                              <span className="text-sm ml-1">
                                {Math.abs(stock.change || 0).toLocaleString()}원
                              </span>
                              <span className="text-sm ml-1">
                                ({(stock.change_percent || 0).toFixed(2)}%)
                              </span>
                            </div>
                          </div>

                          {/* TP/SL 가격 */}
                          {(stock.tp_price || stock.sl_price) && (
                            <div className="text-sm space-y-1">
                              {stock.tp_price && (
                                <div className="flex justify-between">
                                  <span className="text-gray-600">목표가:</span>
                                  <span className="text-red-600 font-medium">
                                    {stock.tp_price.toLocaleString()}원
                                  </span>
                                </div>
                              )}
                              {stock.sl_price && (
                                <div className="flex justify-between">
                                  <span className="text-gray-600">손절가:</span>
                                  <span className="text-blue-600 font-medium">
                                    {stock.sl_price.toLocaleString()}원
                                  </span>
                                </div>
                              )}
                            </div>
                          )}

                          {/* 마지막 업데이트 */}
                          {stock.last_updated && (
                            <div className="text-xs text-gray-500">
                              📅 {new Date(stock.last_updated).toLocaleString()}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2 mt-4">
                      <Button
                        onClick={() => toggleStockMonitoring(stock.code, stock.enabled)}
                        size="sm"
                        variant={stock.enabled ? "secondary" : "primary"}
                        className="flex-1"
                      >
                        {stock.enabled ? '모니터링 중지' : '모니터링 시작'}
                      </Button>
                      <Button
                        onClick={() => window.open(`https://finance.naver.com/item/main.nhn?code=${stock.code}`, '_blank')}
                        size="sm"
                        variant="secondary"
                      >
                        📊 차트보기
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 종목 추가 모달 */}
      <AddStockModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAddStock={handleAddStock}
      />
    </div>
  )
}

export default StockPage