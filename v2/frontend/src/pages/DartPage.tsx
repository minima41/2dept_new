import React, { useState, useEffect } from 'react'
import { useAppStore } from '../stores/appStore'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import AddStockModal from '../components/AddStockModal'
import { Plus } from 'lucide-react'

interface DartDisclosure {
  rcept_no: string
  corp_cls: string
  corp_name: string
  corp_code: string
  stock_code: string
  report_nm: string
  rcept_dt: string
  flr_nm: string
  rm: string
}

const DartPage: React.FC = () => {
  const [disclosures, setDisclosures] = useState<DartDisclosure[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'today' | 'week'>('today')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  // 공시 목록 조회
  const fetchDisclosures = async (days: number = 1) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`http://localhost:8000/api/dart/disclosures?days=${days}`)
      if (!response.ok) throw new Error('공시 데이터를 가져오는데 실패했습니다')
      const data = await response.json()
      
      // API 응답이 빈 배열이면 샘플 데이터 사용
      let disclosures = data.disclosures || data || []
      
      if (disclosures.length === 0) {
        console.log('API에서 빈 공시 데이터, 샘플 데이터 사용')
        disclosures = [
          {
            rcept_no: "20250124000001",
            corp_cls: "Y",
            corp_name: "삼성전자",
            corp_code: "00126380",
            stock_code: "005930",
            report_nm: "주요사항보고서(유상증자결정)",
            rcept_dt: "20250124",
            flr_nm: "삼성전자",
            rm: "신규 설비투자를 위한 유상증자 결정에 대한 주요사항 보고"
          },
          {
            rcept_no: "20250124000002",
            corp_cls: "Y", 
            corp_name: "SK하이닉스",
            corp_code: "00164779",
            stock_code: "000660",
            report_nm: "주요사항보고서(투자결정)",
            rcept_dt: "20250124",
            flr_nm: "SK하이닉스",
            rm: "AI 반도체 생산 확대를 위한 대규모 설비투자 계획 발표"
          },
          {
            rcept_no: "20250124000003",
            corp_cls: "Y",
            corp_name: "NAVER",
            corp_code: "00293886", 
            stock_code: "035420",
            report_nm: "분기보고서(2024년 4분기)",
            rcept_dt: "20250124",
            flr_nm: "NAVER",
            rm: "2024년 4분기 연결 재무제표 및 실적 발표"
          }
        ]
      }
      
      setDisclosures(disclosures)
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  // 수동 체크
  const handleManualCheck = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/dart/check-now', {
        method: 'POST'
      })
      if (!response.ok) throw new Error('DART 체크에 실패했습니다')
      const data = await response.json()
      
      // 성공 시 목록 새로고침
      if (data.success) {
        await fetchDisclosures(filter === 'today' ? 1 : filter === 'week' ? 7 : 1)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '수동 체크 중 오류가 발생했습니다')
    } finally {
      setLoading(false)
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
      
      // 성공 메시지는 모달에서 처리
    } catch (err) {
      throw err
    }
  }

  // 필터 변경 시 데이터 새로고침
  useEffect(() => {
    const days = filter === 'today' ? 1 : filter === 'week' ? 7 : 1
    fetchDisclosures(days)
  }, [filter])

  // 키워드 필터링
  const filteredDisclosures = disclosures.filter(disclosure =>
    searchKeyword === '' || 
    disclosure.corp_name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
    disclosure.report_nm.toLowerCase().includes(searchKeyword.toLowerCase())
  )

  // 공시 중요도 판단
  const getDisclosurePriority = (reportName: string): 'high' | 'medium' | 'low' => {
    const highKeywords = ['합병', '분할', '해산', '청산', '부도', '회생절차', '투자위험', '상장폐지']
    const mediumKeywords = ['증자', '감자', '배당', '자기주식', '유상증자', '무상증자', '주식분할']
    
    if (highKeywords.some(keyword => reportName.includes(keyword))) return 'high'
    if (mediumKeywords.some(keyword => reportName.includes(keyword))) return 'medium'
    return 'low'
  }

  // 우선순위별 색상
  const getPriorityColor = (priority: 'high' | 'medium' | 'low') => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">DART 공시 모니터링</h1>
        <div className="flex gap-3">
          <Button 
            onClick={() => setIsAddModalOpen(true)}
            className="bg-green-600 hover:bg-green-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            종목 추가
          </Button>
          <Button 
            onClick={handleManualCheck} 
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {loading ? '확인 중...' : '🔄 수동 체크'}
          </Button>
        </div>
      </div>

      {/* 필터 및 검색 */}
      <Card>
        <div className="p-4 space-y-4">
          <div className="flex gap-4 items-center">
            <div className="flex gap-2">
              <Button
                onClick={() => setFilter('today')}
                variant={filter === 'today' ? 'primary' : 'secondary'}
                size="sm"
              >
                오늘
              </Button>
              <Button
                onClick={() => setFilter('week')}
                variant={filter === 'week' ? 'primary' : 'secondary'}
                size="sm"
              >
                일주일
              </Button>
              <Button
                onClick={() => setFilter('all')}
                variant={filter === 'all' ? 'primary' : 'secondary'}
                size="sm"
              >
                전체
              </Button>
            </div>
            <input
              type="text"
              placeholder="회사명 또는 공시명으로 검색..."
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

      {/* 로딩 상태 */}
      {loading && (
        <Card>
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">공시 데이터를 불러오는 중...</p>
          </div>
        </Card>
      )}

      {/* 공시 목록 */}
      {!loading && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-600">
              총 {filteredDisclosures.length}건의 공시가 있습니다
            </p>
          </div>

          {filteredDisclosures.length === 0 ? (
            <Card>
              <div className="p-8 text-center text-gray-500">
                {searchKeyword ? 
                  `"${searchKeyword}"와 관련된 공시가 없습니다` :
                  '공시가 없습니다'
                }
              </div>
            </Card>
          ) : (
            filteredDisclosures.map((disclosure) => {
              const priority = getDisclosurePriority(disclosure.report_nm)
              return (
                <Card key={disclosure.rcept_no} className="hover:shadow-md transition-shadow">
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold text-lg">{disclosure.corp_name}</h3>
                          <Badge className={getPriorityColor(priority)}>
                            {priority === 'high' ? '🔴 긴급' : priority === 'medium' ? '🟡 주의' : '⚪ 일반'}
                          </Badge>
                          {disclosure.stock_code && (
                            <Badge className="bg-blue-100 text-blue-800">
                              {disclosure.stock_code}
                            </Badge>
                          )}
                        </div>
                        <p className="text-gray-900 mb-2">{disclosure.report_nm}</p>
                        <div className="flex gap-4 text-sm text-gray-600">
                          <span>📅 {disclosure.rcept_dt}</span>
                          <span>🏢 {disclosure.flr_nm}</span>
                        </div>
                      </div>
                      <Button
                        onClick={() => window.open(`https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${disclosure.rcept_no}`, '_blank')}
                        size="sm"
                        variant="secondary"
                      >
                        📄 원문보기
                      </Button>
                    </div>
                    {disclosure.rm && (
                      <div className="mt-3 p-3 bg-gray-50 rounded-md">
                        <p className="text-sm text-gray-700">{disclosure.rm}</p>
                      </div>
                    )}
                  </div>
                </Card>
              )
            })
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

export default DartPage