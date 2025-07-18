import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { api } from '../services/apiClient'
import { Search, ExternalLink, Settings, RefreshCw } from 'lucide-react'

function DartPage() {
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchCompany, setSearchCompany] = useState('')
  const [page, setPage] = useState(1)

  const { data: disclosures, isLoading, refetch } = useQuery({
    queryKey: ['dart-disclosures', page, searchKeyword, searchCompany],
    queryFn: () => api.dart.disclosures({
      page,
      page_size: 20,
      days: 7,
      keyword: searchKeyword || undefined,
      company: searchCompany || undefined,
    }),
    refetchInterval: 30000, // 30초마다 갱신
  })

  const { data: statistics } = useQuery({
    queryKey: ['dart-statistics'],
    queryFn: api.dart.statistics,
    refetchInterval: 30000,
  })

  const { data: keywords } = useQuery({
    queryKey: ['dart-keywords'],
    queryFn: api.dart.keywords,
  })

  const { data: companies } = useQuery({
    queryKey: ['dart-companies'],
    queryFn: api.dart.companies,
  })

  const handleSearch = () => {
    setPage(1)
    refetch()
  }

  const handleManualCheck = async () => {
    try {
      await api.dart.checkNow()
      refetch()
    } catch (error) {
      console.error('Manual check failed:', error)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">DART 공시 모니터링</h1>
          <p className="text-gray-500 mt-1">실시간 공시 정보를 확인하세요</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={handleManualCheck}>
            <RefreshCw className="h-4 w-4 mr-2" />
            수동 체크
          </Button>
          <Button variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            설정
          </Button>
        </div>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">총 공시 건수</p>
                <p className="text-2xl font-bold">{statistics?.statistics?.total_disclosures || 0}</p>
              </div>
              <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                <ExternalLink className="h-4 w-4 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">매칭 공시</p>
                <p className="text-2xl font-bold">{statistics?.statistics?.matched_disclosures || 0}</p>
              </div>
              <div className="h-8 w-8 bg-green-100 rounded-full flex items-center justify-center">
                <Search className="h-4 w-4 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">발송 알림</p>
                <p className="text-2xl font-bold">{statistics?.statistics?.sent_alerts || 0}</p>
              </div>
              <div className="h-8 w-8 bg-yellow-100 rounded-full flex items-center justify-center">
                <RefreshCw className="h-4 w-4 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">모니터링 기업</p>
                <p className="text-2xl font-bold">{statistics?.statistics?.companies_monitored || 0}</p>
              </div>
              <div className="h-8 w-8 bg-purple-100 rounded-full flex items-center justify-center">
                <Settings className="h-4 w-4 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 검색 필터 */}
      <Card>
        <CardHeader>
          <CardTitle>검색 필터</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                키워드 검색
              </label>
              <Input
                placeholder="키워드를 입력하세요"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                회사명 검색
              </label>
              <Input
                placeholder="회사명을 입력하세요"
                value={searchCompany}
                onChange={(e) => setSearchCompany(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleSearch} className="w-full">
                <Search className="h-4 w-4 mr-2" />
                검색
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 공시 목록 */}
      <Card>
        <CardHeader>
          <CardTitle>공시 목록</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {isLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="text-gray-500 mt-2">로딩 중...</p>
              </div>
            ) : disclosures?.disclosures?.length > 0 ? (
              disclosures.disclosures.map((disclosure: any, index: number) => (
                <div key={index} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="font-medium text-gray-900">{disclosure.corp_name}</h3>
                        <Badge variant="primary">
                          {disclosure.priority_score || 0}점
                        </Badge>
                        <span className="text-sm text-gray-500">
                          {formatDate(disclosure.rcept_dt)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 mb-3">{disclosure.report_nm}</p>
                      <div className="flex items-center space-x-2">
                        {disclosure.matched_keywords?.map((keyword: string, i: number) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(disclosure.dart_url, '_blank')}
                      >
                        <ExternalLink className="h-4 w-4 mr-1" />
                        원문보기
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">공시가 없습니다.</p>
              </div>
            )}
          </div>

          {/* 페이지네이션 */}
          {disclosures?.total_count > 0 && (
            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-gray-500">
                총 {disclosures.total_count}건
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  이전
                </Button>
                <span className="text-sm text-gray-500">
                  {page} / {Math.ceil(disclosures.total_count / 20)}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={!disclosures.has_next}
                >
                  다음
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 키워드 및 기업 정보 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>모니터링 키워드</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {keywords?.keywords?.slice(0, 20).map((keyword: any, index: number) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {keyword.keyword}
                </Badge>
              ))}
            </div>
            <p className="text-sm text-gray-500 mt-2">
              총 {keywords?.total_count || 0}개 키워드
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>관심 기업</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {companies?.companies?.slice(0, 10).map((company: any, index: number) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span>{company.corp_name}</span>
                  <Badge variant={company.is_active ? 'success' : 'secondary'} className="text-xs">
                    {company.is_active ? '활성' : '비활성'}
                  </Badge>
                </div>
              ))}
            </div>
            <p className="text-sm text-gray-500 mt-2">
              총 {companies?.total_count || 0}개 기업
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default DartPage