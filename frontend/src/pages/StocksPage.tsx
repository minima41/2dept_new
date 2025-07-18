import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { api } from '../services/apiClient'
import { Plus, Search, Settings, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react'

function StocksPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [newStock, setNewStock] = useState({
    code: '',
    name: '',
    purchase_price: '',
    quantity: '',
    take_profit: '',
    stop_loss: '',
    alert_enabled: true,
  })

  const { data: monitoringStocks, isLoading, refetch } = useQuery({
    queryKey: ['monitoring-stocks'],
    queryFn: api.stocks.monitoring,
    refetchInterval: 10000, // 10초마다 갱신
  })

  const { data: statistics } = useQuery({
    queryKey: ['stock-statistics'],
    queryFn: api.stocks.statistics,
    refetchInterval: 30000,
  })

  const { data: marketInfo } = useQuery({
    queryKey: ['market-info'],
    queryFn: api.stocks.marketInfo,
    refetchInterval: 60000,
  })

  const { data: searchResults } = useQuery({
    queryKey: ['stock-search', searchQuery],
    queryFn: () => api.stocks.search(searchQuery),
    enabled: searchQuery.length >= 2,
  })

  const handleAddStock = async () => {
    try {
      await api.stocks.addMonitoring({
        ...newStock,
        purchase_price: parseFloat(newStock.purchase_price),
        quantity: parseInt(newStock.quantity),
        take_profit: newStock.take_profit ? parseFloat(newStock.take_profit) : undefined,
        stop_loss: newStock.stop_loss ? parseFloat(newStock.stop_loss) : undefined,
      })
      setShowAddForm(false)
      setNewStock({
        code: '',
        name: '',
        purchase_price: '',
        quantity: '',
        take_profit: '',
        stop_loss: '',
        alert_enabled: true,
      })
      refetch()
    } catch (error) {
      console.error('Failed to add stock:', error)
    }
  }

  const handleRemoveStock = async (code: string) => {
    if (confirm('이 종목을 모니터링에서 제거하시겠습니까?')) {
      try {
        await api.stocks.removeMonitoring(code)
        refetch()
      } catch (error) {
        console.error('Failed to remove stock:', error)
      }
    }
  }

  const handleManualCheck = async () => {
    try {
      await api.stocks.checkNow()
      refetch()
    } catch (error) {
      console.error('Manual check failed:', error)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR').format(amount)
  }

  const formatPercent = (percent: number) => {
    return `${percent > 0 ? '+' : ''}${percent.toFixed(2)}%`
  }

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">주가 모니터링</h1>
          <p className="text-gray-500 mt-1">실시간 주가 정보를 확인하세요</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={marketInfo?.market_info?.is_trading_hours ? 'success' : 'secondary'}>
            {marketInfo?.market_info?.is_trading_hours ? '장 중' : '장 마감'}
          </Badge>
          <Button variant="outline" onClick={handleManualCheck}>
            <RefreshCw className="h-4 w-4 mr-2" />
            수동 체크
          </Button>
          <Button onClick={() => setShowAddForm(!showAddForm)}>
            <Plus className="h-4 w-4 mr-2" />
            종목 추가
          </Button>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">총 종목 수</p>
                <p className="text-2xl font-bold">{statistics?.statistics?.total_stocks || 0}</p>
              </div>
              <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                <TrendingUp className="h-4 w-4 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">포트폴리오 가치</p>
                <p className="text-2xl font-bold">
                  {statistics?.statistics?.total_portfolio_value 
                    ? `${formatCurrency(statistics.statistics.total_portfolio_value)}원`
                    : '0원'
                  }
                </p>
              </div>
              <div className="h-8 w-8 bg-green-100 rounded-full flex items-center justify-center">
                <TrendingUp className="h-4 w-4 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">총 손익</p>
                <p className={`text-2xl font-bold ${
                  statistics?.statistics?.total_profit_loss > 0 ? 'text-red-600' : 
                  statistics?.statistics?.total_profit_loss < 0 ? 'text-blue-600' : 'text-gray-600'
                }`}>
                  {statistics?.statistics?.total_profit_loss 
                    ? `${formatCurrency(statistics.statistics.total_profit_loss)}원`
                    : '0원'
                  }
                </p>
              </div>
              <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                statistics?.statistics?.total_profit_loss > 0 ? 'bg-red-100' : 
                statistics?.statistics?.total_profit_loss < 0 ? 'bg-blue-100' : 'bg-gray-100'
              }`}>
                {statistics?.statistics?.total_profit_loss > 0 ? (
                  <TrendingUp className="h-4 w-4 text-red-600" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-blue-600" />
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">오늘 알림</p>
                <p className="text-2xl font-bold">{statistics?.statistics?.today_alerts || 0}</p>
              </div>
              <div className="h-8 w-8 bg-yellow-100 rounded-full flex items-center justify-center">
                <Settings className="h-4 w-4 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 종목 추가 폼 */}
      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>종목 추가</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  종목 검색
                </label>
                <Input
                  placeholder="종목명 또는 코드 입력"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchResults?.results && searchResults.results.length > 0 && (
                  <div className="mt-2 border rounded-md max-h-40 overflow-y-auto">
                    {searchResults.results.map((stock: any, index: number) => (
                      <div
                        key={index}
                        className="p-2 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                        onClick={() => {
                          setNewStock(prev => ({
                            ...prev,
                            code: stock.code,
                            name: stock.name,
                          }))
                          setSearchQuery('')
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{stock.name}</span>
                          <span className="text-sm text-gray-500">{stock.code}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  종목코드
                </label>
                <Input
                  placeholder="ex) 005930"
                  value={newStock.code}
                  onChange={(e) => setNewStock(prev => ({...prev, code: e.target.value}))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  종목명
                </label>
                <Input
                  placeholder="ex) 삼성전자"
                  value={newStock.name}
                  onChange={(e) => setNewStock(prev => ({...prev, name: e.target.value}))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  취득가
                </label>
                <Input
                  type="number"
                  placeholder="ex) 70000"
                  value={newStock.purchase_price}
                  onChange={(e) => setNewStock(prev => ({...prev, purchase_price: e.target.value}))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  수량
                </label>
                <Input
                  type="number"
                  placeholder="ex) 100"
                  value={newStock.quantity}
                  onChange={(e) => setNewStock(prev => ({...prev, quantity: e.target.value}))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  목표가 (선택)
                </label>
                <Input
                  type="number"
                  placeholder="ex) 80000"
                  value={newStock.take_profit}
                  onChange={(e) => setNewStock(prev => ({...prev, take_profit: e.target.value}))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  손절가 (선택)
                </label>
                <Input
                  type="number"
                  placeholder="ex) 60000"
                  value={newStock.stop_loss}
                  onChange={(e) => setNewStock(prev => ({...prev, stop_loss: e.target.value}))}
                />
              </div>
            </div>
            <div className="flex items-center justify-end space-x-2 mt-4">
              <Button variant="outline" onClick={() => setShowAddForm(false)}>
                취소
              </Button>
              <Button onClick={handleAddStock}>
                추가
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 모니터링 종목 목록 */}
      <Card>
        <CardHeader>
          <CardTitle>모니터링 종목</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3">종목명</th>
                  <th className="text-right p-3">현재가</th>
                  <th className="text-right p-3">변동률</th>
                  <th className="text-right p-3">취득가</th>
                  <th className="text-right p-3">손익률</th>
                  <th className="text-right p-3">목표가</th>
                  <th className="text-right p-3">손절가</th>
                  <th className="text-center p-3">알림</th>
                  <th className="text-center p-3">액션</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                      <p className="text-gray-500 mt-2">로딩 중...</p>
                    </td>
                  </tr>
                ) : monitoringStocks?.stocks?.length > 0 ? (
                  monitoringStocks.stocks.map((stock: any, index: number) => (
                    <tr key={index} className="border-b hover:bg-gray-50">
                      <td className="p-3">
                        <div>
                          <div className="font-medium">{stock.name}</div>
                          <div className="text-sm text-gray-500">{stock.code}</div>
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        {stock.current_price ? `${formatCurrency(stock.current_price)}원` : '-'}
                      </td>
                      <td className={`p-3 text-right ${
                        stock.change_rate > 0 ? 'text-red-600' : 
                        stock.change_rate < 0 ? 'text-blue-600' : 'text-gray-600'
                      }`}>
                        {stock.change_rate ? formatPercent(stock.change_rate) : '-'}
                      </td>
                      <td className="p-3 text-right">
                        {formatCurrency(stock.purchase_price)}원
                      </td>
                      <td className={`p-3 text-right ${
                        stock.profit_loss_rate > 0 ? 'text-red-600' : 
                        stock.profit_loss_rate < 0 ? 'text-blue-600' : 'text-gray-600'
                      }`}>
                        {stock.profit_loss_rate ? formatPercent(stock.profit_loss_rate) : '-'}
                      </td>
                      <td className="p-3 text-right">
                        {stock.take_profit ? `${formatCurrency(stock.take_profit)}원` : '-'}
                      </td>
                      <td className="p-3 text-right">
                        {stock.stop_loss ? `${formatCurrency(stock.stop_loss)}원` : '-'}
                      </td>
                      <td className="p-3 text-center">
                        <Badge variant={stock.alert_enabled ? 'success' : 'secondary'}>
                          {stock.alert_enabled ? 'ON' : 'OFF'}
                        </Badge>
                      </td>
                      <td className="p-3 text-center">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemoveStock(stock.code)}
                        >
                          제거
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="text-center py-8">
                      <p className="text-gray-500">모니터링 중인 종목이 없습니다.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default StocksPage