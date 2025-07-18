import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'

function SettingsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">설정</h1>
        <p className="text-gray-500 mt-1">시스템 설정 및 환경 구성</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>시스템 설정</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">설정 기능은 향후 구현 예정입니다.</p>
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