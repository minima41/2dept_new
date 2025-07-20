import { StockStatistics } from '../types'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Badge } from './ui/Badge'
import { TrendingUp, TrendingDown, PieChart, Target, Percent } from 'lucide-react'

interface MezzanineStatisticsProps {
  statistics: StockStatistics
}

function MezzanineStatistics({ statistics }: MezzanineStatisticsProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR').format(amount)
  }

  const formatPercent = (percent: number) => {
    return `${percent > 0 ? '+' : ''}${percent.toFixed(2)}%`
  }

  const getProfitColor = (profit: number) => {
    return profit > 0 ? 'text-red-600' : profit < 0 ? 'text-blue-600' : 'text-gray-600'
  }


  // 메자닌 대비 기타의 비율 계산
  const totalInvestment = statistics.total_investment || 0
  const mezzanineRatio = totalInvestment > 0 ? (statistics.mezzanine_investment / totalInvestment) * 100 : 0
  const otherRatio = totalInvestment > 0 ? (statistics.other_investment / totalInvestment) * 100 : 0

  return (
    <div className="space-y-6">
      {/* 전체 요약 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <PieChart className="h-5 w-5" />
            <span>포트폴리오 요약</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold">{statistics.total_stocks}</p>
              <p className="text-sm text-gray-500">총 종목 수</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{formatCurrency(statistics.total_portfolio_value)}원</p>
              <p className="text-sm text-gray-500">포트폴리오 가치</p>
            </div>
            <div className="text-center">
              <p className={`text-2xl font-bold ${getProfitColor(statistics.total_profit_loss)}`}>
                {formatCurrency(statistics.total_profit_loss)}원
              </p>
              <p className="text-sm text-gray-500">총 손익</p>
            </div>
            <div className="text-center">
              <p className={`text-2xl font-bold ${getProfitColor(statistics.total_profit_loss)}`}>
                {formatPercent(statistics.total_profit_loss_rate)}
              </p>
              <p className="text-sm text-gray-500">총 수익률</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 카테고리별 비교 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 메자닌 통계 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <Target className="h-5 w-5 text-purple-600" />
                <span>메자닌 투자</span>
              </CardTitle>
              <Badge variant="primary" className="text-xs">
                {mezzanineRatio.toFixed(1)}%
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">종목 수</p>
                <p className="text-xl font-bold">{statistics.mezzanine_stocks}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">투자금액</p>
                <p className="text-lg font-semibold">
                  {formatCurrency(statistics.mezzanine_investment)}원
                </p>
              </div>
            </div>
            
            <div>
              <p className="text-sm text-gray-500">평가금액</p>
              <p className="text-xl font-bold">
                {formatCurrency(statistics.mezzanine_portfolio_value)}원
              </p>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
              <div>
                <p className="text-sm text-gray-600">손익</p>
                <p className={`text-lg font-bold ${getProfitColor(statistics.mezzanine_profit_loss)}`}>
                  {formatCurrency(statistics.mezzanine_profit_loss)}원
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">수익률</p>
                <div className="flex items-center space-x-2">
                  <p className={`text-lg font-bold ${getProfitColor(statistics.mezzanine_profit_loss)}`}>
                    {formatPercent(statistics.mezzanine_profit_loss_rate)}
                  </p>
                  {statistics.mezzanine_profit_loss > 0 ? (
                    <TrendingUp className="h-4 w-4 text-red-600" />
                  ) : statistics.mezzanine_profit_loss < 0 ? (
                    <TrendingDown className="h-4 w-4 text-blue-600" />
                  ) : null}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 기타 투자 통계 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5 text-blue-600" />
                <span>기타 투자</span>
              </CardTitle>
              <Badge variant="secondary" className="text-xs">
                {otherRatio.toFixed(1)}%
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">종목 수</p>
                <p className="text-xl font-bold">{statistics.other_stocks}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">투자금액</p>
                <p className="text-lg font-semibold">
                  {formatCurrency(statistics.other_investment)}원
                </p>
              </div>
            </div>
            
            <div>
              <p className="text-sm text-gray-500">평가금액</p>
              <p className="text-xl font-bold">
                {formatCurrency(statistics.other_portfolio_value)}원
              </p>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div>
                <p className="text-sm text-gray-600">손익</p>
                <p className={`text-lg font-bold ${getProfitColor(statistics.other_profit_loss)}`}>
                  {formatCurrency(statistics.other_profit_loss)}원
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">수익률</p>
                <div className="flex items-center space-x-2">
                  <p className={`text-lg font-bold ${getProfitColor(statistics.other_profit_loss)}`}>
                    {formatPercent(statistics.other_profit_loss_rate)}
                  </p>
                  {statistics.other_profit_loss > 0 ? (
                    <TrendingUp className="h-4 w-4 text-red-600" />
                  ) : statistics.other_profit_loss < 0 ? (
                    <TrendingDown className="h-4 w-4 text-blue-600" />
                  ) : null}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 포트폴리오 구성 비율 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Percent className="h-5 w-5" />
            <span>포트폴리오 구성</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* 시각적 비율 바 */}
            <div className="relative h-6 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="absolute left-0 top-0 h-full bg-purple-500 transition-all duration-300"
                style={{ width: `${mezzanineRatio}%` }}
              />
              <div 
                className="absolute top-0 h-full bg-blue-500 transition-all duration-300"
                style={{ left: `${mezzanineRatio}%`, width: `${otherRatio}%` }}
              />
            </div>
            
            {/* 범례 */}
            <div className="flex items-center justify-center space-x-6">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full" />
                <span className="text-sm">메자닌 ({mezzanineRatio.toFixed(1)}%)</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full" />
                <span className="text-sm">기타 ({otherRatio.toFixed(1)}%)</span>
              </div>
            </div>
            
            {/* 상세 정보 */}
            <div className="grid grid-cols-2 gap-4 pt-2 border-t">
              <div className="text-center">
                <p className="text-sm text-gray-500">메자닌 평균 수익률</p>
                <p className={`text-lg font-bold ${getProfitColor(statistics.mezzanine_profit_loss)}`}>
                  {formatPercent(statistics.mezzanine_profit_loss_rate)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">기타 평균 수익률</p>
                <p className={`text-lg font-bold ${getProfitColor(statistics.other_profit_loss)}`}>
                  {formatPercent(statistics.other_profit_loss_rate)}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default MezzanineStatistics