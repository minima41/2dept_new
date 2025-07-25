import React, { useState } from 'react'
import { X, Plus } from 'lucide-react'
import { Button } from './ui/Button'
import { Card } from './ui/Card'

interface AddStockModalProps {
  isOpen: boolean
  onClose: () => void
  onAddStock: (stockData: StockFormData) => Promise<void>
}

interface StockFormData {
  stock_code: string
  stock_name: string
  target_price: number
  stop_loss_price: number
  purchase_price: number
  quantity: number
  notes: string
}

const AddStockModal: React.FC<AddStockModalProps> = ({ isOpen, onClose, onAddStock }) => {
  const [formData, setFormData] = useState<StockFormData>({
    stock_code: '',
    stock_name: '',
    target_price: 0,
    stop_loss_price: 0,
    purchase_price: 0,
    quantity: 0,
    notes: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 종목코드 조회
  const handleStockCodeSearch = async () => {
    if (!formData.stock_code || formData.stock_code.length !== 6) {
      setError('6자리 종목코드를 입력해주세요')
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      // 종목 정보 조회 API 호출
      const response = await fetch(`http://localhost:8000/api/stocks/info/${formData.stock_code}`)
      if (!response.ok) {
        throw new Error('종목 정보를 찾을 수 없습니다')
      }
      
      const data = await response.json()
      setFormData(prev => ({
        ...prev,
        stock_name: data.name || `종목${formData.stock_code}`
      }))
    } catch (err) {
      // API 실패 시 수동 입력 허용
      console.warn('종목 정보 조회 실패:', err)
      setFormData(prev => ({
        ...prev,
        stock_name: `종목${formData.stock_code}`
      }))
    } finally {
      setLoading(false)
    }
  }

  // 폼 제출
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.stock_code || !formData.stock_name) {
      setError('종목코드와 종목명은 필수입니다')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await onAddStock(formData)
      // 성공 시 폼 초기화 및 모달 닫기
      setFormData({
        stock_code: '',
        stock_name: '',
        target_price: 0,
        stop_loss_price: 0,
        purchase_price: 0,
        quantity: 0,
        notes: ''
      })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '종목 추가 중 오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* 헤더 */}
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-gray-900">종목 추가</h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              disabled={loading}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600 text-sm">❌ {error}</p>
            </div>
          )}

          {/* 폼 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 종목코드 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                종목코드 *
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={formData.stock_code}
                  onChange={(e) => setFormData(prev => ({ ...prev, stock_code: e.target.value }))}
                  placeholder="예: 005930"
                  maxLength={6}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <Button
                  type="button"
                  onClick={handleStockCodeSearch}
                  disabled={loading || !formData.stock_code}
                  size="sm"
                >
                  조회
                </Button>
              </div>
            </div>

            {/* 종목명 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                종목명 *
              </label>
              <input
                type="text"
                value={formData.stock_name}
                onChange={(e) => setFormData(prev => ({ ...prev, stock_name: e.target.value }))}
                placeholder="종목명"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            {/* 가격 정보 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  매수가
                </label>
                <input
                  type="number"
                  value={formData.purchase_price || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, purchase_price: Number(e.target.value) }))}
                  placeholder="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  수량
                </label>
                <input
                  type="number"
                  value={formData.quantity || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, quantity: Number(e.target.value) }))}
                  placeholder="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* 목표가/손절가 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  목표가
                </label>
                <input
                  type="number"
                  value={formData.target_price || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, target_price: Number(e.target.value) }))}
                  placeholder="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  손절가
                </label>
                <input
                  type="number"
                  value={formData.stop_loss_price || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, stop_loss_price: Number(e.target.value) }))}
                  placeholder="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* 메모 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                메모
              </label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="추가 정보나 메모..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* 버튼 */}
            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
                disabled={loading}
                className="flex-1"
              >
                취소
              </Button>
              <Button
                type="submit"
                disabled={loading || !formData.stock_code || !formData.stock_name}
                className="flex-1"
              >
                {loading ? '추가 중...' : '추가'}
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </div>
  )
}

export default AddStockModal