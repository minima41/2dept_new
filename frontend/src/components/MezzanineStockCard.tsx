import { useState } from 'react'
import { MonitoringStock } from '../types'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Settings, Target, Plus, X } from 'lucide-react'

interface MezzanineStockCardProps {
  stock: MonitoringStock
  onUpdateStock: (code: string, updates: Partial<MonitoringStock>) => void
  onRemoveStock: (code: string) => void
}

function MezzanineStockCard({ stock, onUpdateStock, onRemoveStock }: MezzanineStockCardProps) {
  const [showSettings, setShowSettings] = useState(false)
  const [showAlertSettings, setShowAlertSettings] = useState(false)
  const [editValues, setEditValues] = useState({
    conversion_price: stock.conversion_price?.toString() || '',
    conversion_price_floor: stock.conversion_price_floor?.toString() || '',
    take_profit: stock.take_profit?.toString() || '',
    stop_loss: stock.stop_loss?.toString() || ''
  })
  const [newAlertPrice, setNewAlertPrice] = useState({
    price: '',
    alert_type: 'parity',
    description: ''
  })

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR').format(amount)
  }

  const formatPercent = (percent: number) => {
    return `${percent > 0 ? '+' : ''}${percent.toFixed(2)}%`
  }

  const getParityColor = (parity?: number) => {
    if (!parity) return 'text-gray-500'
    return parity >= 100 ? 'text-green-600' : 'text-red-600'
  }

  const getParityBadgeVariant = (parity?: number) => {
    if (!parity) return 'secondary'
    return parity >= 100 ? 'success' : 'danger'
  }

  const handleUpdateSettings = () => {
    const updates: Partial<MonitoringStock> = {}
    
    if (editValues.conversion_price) {
      updates.conversion_price = parseFloat(editValues.conversion_price)
    }
    if (editValues.conversion_price_floor) {
      updates.conversion_price_floor = parseFloat(editValues.conversion_price_floor)
    }
    if (editValues.take_profit) {
      updates.take_profit = parseFloat(editValues.take_profit)
    }
    if (editValues.stop_loss) {
      updates.stop_loss = parseFloat(editValues.stop_loss)
    }

    onUpdateStock(stock.code, updates)
    setShowSettings(false)
  }

  const handleAddAlertPrice = () => {
    if (!newAlertPrice.price) return

    const alertPrice = {
      price: parseFloat(newAlertPrice.price),
      alert_type: newAlertPrice.alert_type,
      is_enabled: true,
      description: newAlertPrice.description || undefined
    }

    const updatedAlertPrices = [...(stock.alert_prices || []), alertPrice]
    onUpdateStock(stock.code, { alert_prices: updatedAlertPrices })
    
    setNewAlertPrice({ price: '', alert_type: 'parity', description: '' })
  }

  const handleRemoveAlertPrice = (index: number) => {
    const updatedAlertPrices = stock.alert_prices?.filter((_, i) => i !== index) || []
    onUpdateStock(stock.code, { alert_prices: updatedAlertPrices })
  }

  const effective_acquisition_price = stock.acquisition_price || stock.purchase_price

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{stock.name}</CardTitle>
            <p className="text-sm text-gray-500">{stock.code}</p>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="primary" className="text-xs">메자닌</Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSettings(!showSettings)}
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 현재가 및 변동률 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">현재가</p>
            <p className="text-xl font-bold">
              {stock.current_price ? `${formatCurrency(stock.current_price)}원` : '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">변동률</p>
            <p className={`text-xl font-bold ${
              stock.change_rate && stock.change_rate > 0 ? 'text-red-600' : 
              stock.change_rate && stock.change_rate < 0 ? 'text-blue-600' : 'text-gray-600'
            }`}>
              {stock.change_rate ? formatPercent(stock.change_rate) : '-'}
            </p>
          </div>
        </div>

        {/* 패리티 정보 */}
        <div className="grid grid-cols-2 gap-4 p-3 bg-gray-50 rounded-lg">
          <div>
            <p className="text-sm text-gray-500">패리티</p>
            <div className="flex items-center space-x-2">
              <p className={`text-lg font-bold ${getParityColor(stock.parity)}`}>
                {stock.parity ? `${stock.parity.toFixed(2)}%` : '-'}
              </p>
              <Badge variant={getParityBadgeVariant(stock.parity)} className="text-xs">
                {stock.parity && stock.parity >= 100 ? '돌파' : '미달'}
              </Badge>
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-500">패리티(바닥가)</p>
            <p className={`text-lg font-bold ${getParityColor(stock.parity_floor)}`}>
              {stock.parity_floor ? `${stock.parity_floor.toFixed(2)}%` : '-'}
            </p>
          </div>
        </div>

        {/* 수익률 및 손익 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">수익률</p>
            <p className={`text-lg font-bold ${
              stock.profit_loss_rate && stock.profit_loss_rate > 0 ? 'text-red-600' : 
              stock.profit_loss_rate && stock.profit_loss_rate < 0 ? 'text-blue-600' : 'text-gray-600'
            }`}>
              {stock.profit_loss_rate ? formatPercent(stock.profit_loss_rate) : '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">손익금액</p>
            <p className={`text-lg font-bold ${
              stock.profit_loss && stock.profit_loss > 0 ? 'text-red-600' : 
              stock.profit_loss && stock.profit_loss < 0 ? 'text-blue-600' : 'text-gray-600'
            }`}>
              {stock.profit_loss ? `${formatCurrency(stock.profit_loss)}원` : '-'}
            </p>
          </div>
        </div>

        {/* 투자 정보 */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-gray-500">취득가</p>
            <p className="font-medium">{formatCurrency(effective_acquisition_price)}원</p>
          </div>
          <div>
            <p className="text-gray-500">보유수량</p>
            <p className="font-medium">{formatCurrency(stock.quantity)}주</p>
          </div>
          <div>
            <p className="text-gray-500">투자금액</p>
            <p className="font-medium">{formatCurrency(effective_acquisition_price * stock.quantity)}원</p>
          </div>
        </div>

        {/* 전환가 정보 */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">전환가</p>
            <p className="font-medium">
              {stock.conversion_price ? `${formatCurrency(stock.conversion_price)}원` : '미설정'}
            </p>
          </div>
          <div>
            <p className="text-gray-500">전환가(바닥가)</p>
            <p className="font-medium">
              {stock.conversion_price_floor ? `${formatCurrency(stock.conversion_price_floor)}원` : '미설정'}
            </p>
          </div>
        </div>

        {/* 알림 설정 */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center space-x-2">
            <Badge variant={stock.alert_enabled ? 'success' : 'secondary'} className="text-xs">
              {stock.alert_enabled ? '알림 ON' : '알림 OFF'}
            </Badge>
            {stock.alert_prices && stock.alert_prices.length > 0 && (
              <Badge variant="primary" className="text-xs">
                사용자 알림 {stock.alert_prices.length}개
              </Badge>
            )}
          </div>
          <div className="flex items-center space-x-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAlertSettings(!showAlertSettings)}
            >
              <Target className="h-3 w-3 mr-1" />
              알림설정
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onRemoveStock(stock.code)}
              className="text-red-600 hover:bg-red-50"
            >
              제거
            </Button>
          </div>
        </div>

        {/* 설정 패널 */}
        {showSettings && (
          <div className="p-4 bg-gray-50 rounded-lg space-y-3">
            <h4 className="font-medium text-sm">메자닌 설정</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-600">전환가</label>
                <Input
                  type="number"
                  placeholder="전환가"
                  value={editValues.conversion_price}
                  onChange={(e) => setEditValues(prev => ({...prev, conversion_price: e.target.value}))}
                  className="text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-600">전환가(바닥가)</label>
                <Input
                  type="number"
                  placeholder="전환가 바닥가"
                  value={editValues.conversion_price_floor}
                  onChange={(e) => setEditValues(prev => ({...prev, conversion_price_floor: e.target.value}))}
                  className="text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-600">목표가</label>
                <Input
                  type="number"
                  placeholder="목표가"
                  value={editValues.take_profit}
                  onChange={(e) => setEditValues(prev => ({...prev, take_profit: e.target.value}))}
                  className="text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-600">손절가</label>
                <Input
                  type="number"
                  placeholder="손절가"
                  value={editValues.stop_loss}
                  onChange={(e) => setEditValues(prev => ({...prev, stop_loss: e.target.value}))}
                  className="text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-2">
              <Button variant="outline" size="sm" onClick={() => setShowSettings(false)}>
                취소
              </Button>
              <Button size="sm" onClick={handleUpdateSettings}>
                저장
              </Button>
            </div>
          </div>
        )}

        {/* 알림 설정 패널 */}
        {showAlertSettings && (
          <div className="p-4 bg-gray-50 rounded-lg space-y-3">
            <h4 className="font-medium text-sm">사용자 정의 알림</h4>
            
            {/* 기존 알림 목록 */}
            {stock.alert_prices && stock.alert_prices.length > 0 && (
              <div className="space-y-2">
                {stock.alert_prices.map((alertPrice, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-white rounded border">
                    <div className="text-sm">
                      <span className="font-medium">
                        {alertPrice.alert_type === 'parity' ? `패리티 ${alertPrice.price}%` : 
                         alertPrice.alert_type === 'above' ? `${formatCurrency(alertPrice.price)}원 이상` :
                         alertPrice.alert_type === 'below' ? `${formatCurrency(alertPrice.price)}원 이하` :
                         `${alertPrice.price} ${alertPrice.alert_type}`}
                      </span>
                      {alertPrice.description && (
                        <span className="text-gray-500 ml-2">({alertPrice.description})</span>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveAlertPrice(index)}
                      className="text-red-600 hover:bg-red-50"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
            
            {/* 새 알림 추가 */}
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <select
                  value={newAlertPrice.alert_type}
                  onChange={(e) => setNewAlertPrice(prev => ({...prev, alert_type: e.target.value}))}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="parity">패리티(%)</option>
                  <option value="above">가격이상</option>
                  <option value="below">가격이하</option>
                </select>
                <Input
                  type="number"
                  placeholder="값"
                  value={newAlertPrice.price}
                  onChange={(e) => setNewAlertPrice(prev => ({...prev, price: e.target.value}))}
                  className="text-sm"
                />
                <Input
                  placeholder="설명(선택)"
                  value={newAlertPrice.description}
                  onChange={(e) => setNewAlertPrice(prev => ({...prev, description: e.target.value}))}
                  className="text-sm"
                />
              </div>
              <Button size="sm" onClick={handleAddAlertPrice} disabled={!newAlertPrice.price}>
                <Plus className="h-3 w-3 mr-1" />
                알림 추가
              </Button>
            </div>
            
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setShowAlertSettings(false)}>
                닫기
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default MezzanineStockCard