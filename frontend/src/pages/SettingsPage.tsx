import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { api } from '../services/apiClient'
import { Mail, Send, CheckCircle, XCircle } from 'lucide-react'

function SettingsPage() {
  const [emailTestLoading, setEmailTestLoading] = useState(false)
  const [emailTestResult, setEmailTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleTestDailySummaryEmail = async () => {
    setEmailTestLoading(true)
    setEmailTestResult(null)
    
    try {
      const response = await api.email.testDailySummary()
      setEmailTestResult({
        success: response.success,
        message: response.message
      })
    } catch (error) {
      setEmailTestResult({
        success: false,
        message: '이메일 테스트 요청에 실패했습니다.'
      })
    } finally {
      setEmailTestLoading(false)
    }
  }
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">설정</h1>
        <p className="text-gray-500 mt-1">시스템 설정 및 환경 구성</p>
      </div>

      {/* 이메일 시스템 테스트 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Mail className="h-5 w-5" />
            <span>이메일 시스템</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">일일 마감 요약 이메일</h3>
            <p className="text-gray-500 text-sm mb-4">
              매일 15:35에 자동으로 발송되는 일일 마감 요약 이메일을 테스트할 수 있습니다.
              메자닌/기타 투자 분리된 HTML 테이블과 포트폴리오 통계가 포함됩니다.
            </p>
            
            <div className="flex items-center space-x-4">
              <Button
                onClick={handleTestDailySummaryEmail}
                disabled={emailTestLoading}
                className="flex items-center space-x-2"
              >
                <Send className="h-4 w-4" />
                <span>{emailTestLoading ? '전송 중...' : '테스트 이메일 발송'}</span>
              </Button>
              
              {emailTestResult && (
                <div className="flex items-center space-x-2">
                  {emailTestResult.success ? (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                  <Badge variant={emailTestResult.success ? 'success' : 'danger'}>
                    {emailTestResult.message}
                  </Badge>
                </div>
              )}
            </div>
            
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <h4 className="text-sm font-medium text-blue-900 mb-2">자동 발송 일정</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• 매일 오후 3시 35분 (15:35) 자동 발송</li>
                <li>• 메자닌 투자: 패리티, 전환가 포함</li>
                <li>• 기타 투자: 수익률, 손익금액 포함</li>
                <li>• 등락률 기준 정렬 및 색상 코딩</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 기타 설정 */}
      <Card>
        <CardHeader>
          <CardTitle>기타 설정</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">추가 설정 기능은 향후 구현 예정입니다.</p>
            <p className="text-gray-400 text-sm mt-2">
              DART 키워드, 관심 기업, 알림 설정 등을 관리할 수 있습니다.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsPage