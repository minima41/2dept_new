import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'

function PortfolioPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">포트폴리오 관리</h1>
        <p className="text-gray-500 mt-1">포트폴리오 통합 관리 기능</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>포트폴리오 관리</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">포트폴리오 관리 기능은 향후 구현 예정입니다.</p>
            <p className="text-gray-400 text-sm mt-2">
              현재는 주가 모니터링 페이지에서 종목별 손익을 확인할 수 있습니다.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default PortfolioPage