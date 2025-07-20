// 공통 타입 정의

export interface ApiResponse<T> {
  data: T
  message?: string
  success?: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total_count: number
  page: number
  page_size: number
  has_next: boolean
}

// DART 관련 타입
export interface DartDisclosure {
  rcept_no: string
  corp_cls: string
  corp_code: string
  corp_name: string
  report_nm: string
  rcept_dt: string
  flr_nm: string
  rm?: string
  stock_code?: string
  matched_keywords: string[]
  priority_score: number
  dart_url: string
}

export interface DartKeyword {
  keyword: string
  weight: number
  category: string
  is_active: boolean
}

export interface DartCompany {
  stock_code: string
  corp_code: string
  corp_name: string
  is_active: boolean
  last_checked?: string
}

export interface DartStatistics {
  total_disclosures: number
  matched_disclosures: number
  sent_alerts: number
  companies_monitored: number
  keywords_count: number
  last_check_time?: string
  next_check_time?: string
}

// 주가 관련 타입
export interface StockData {
  code: string
  name: string
  current_price: number
  prev_close: number
  change: number
  change_rate: number
  volume: number
  trading_value: number
  market_cap?: number
  high?: number
  low?: number
  open_price?: number
  updated_at: string
}

export interface MonitoringStock {
  code: string
  name: string
  purchase_price: number
  acquisition_price?: number
  quantity: number
  take_profit?: number
  stop_loss?: number
  daily_surge_threshold: number
  daily_drop_threshold: number
  alert_enabled: boolean
  last_updated: string
  
  // 메자닌 투자 관련 필드
  category: 'mezzanine' | 'other'
  conversion_price?: number
  conversion_price_floor?: number
  
  // 복잡한 알림 시스템
  triggered_alerts: string[]
  alert_prices: AlertPrice[]
  daily_up_alert_sent: boolean
  daily_down_alert_sent: boolean
  
  // 런타임 데이터
  current_price?: number
  change_rate?: number
  profit_loss?: number
  profit_loss_rate?: number
  parity?: number
  parity_floor?: number
}

export interface AlertPrice {
  price: number
  alert_type: string
  is_enabled: boolean
  description?: string
}

export interface StockAlert {
  id?: number
  stock_code: string
  stock_name: string
  alert_type: 'take_profit' | 'stop_loss' | 'daily_surge' | 'daily_drop' | 'custom'
  target_price: number
  current_price: number
  change_rate: number
  message: string
  triggered_at: string
  is_sent: boolean
  sent_at?: string
}

export interface StockStatistics {
  // 전체 통계
  total_stocks: number
  active_alerts: number
  today_alerts: number
  market_status: 'open' | 'closed' | 'pre_market' | 'after_market'
  last_update?: string
  total_portfolio_value: number
  total_profit_loss: number
  total_profit_loss_rate: number
  total_investment: number
  
  // 메자닌 통계
  mezzanine_stocks: number
  mezzanine_portfolio_value: number
  mezzanine_profit_loss: number
  mezzanine_profit_loss_rate: number
  mezzanine_investment: number
  
  // 기타 통계
  other_stocks: number
  other_portfolio_value: number
  other_profit_loss: number
  other_profit_loss_rate: number
  other_investment: number
}

export interface MarketInfo {
  status: 'open' | 'closed' | 'pre_market' | 'after_market'
  open_time: string
  close_time: string
  current_time: string
  is_trading_hours: boolean
  next_open?: string
}

// WebSocket 메시지 타입
export interface WebSocketMessage {
  type: 'dart_update' | 'stock_update' | 'alert_triggered' | 'system_status' | 'user_connected' | 'error' | 'ping'
  data?: any
  timestamp?: string
}

// 알림 타입
export interface Alert {
  id: string
  type: 'dart' | 'stock' | 'system'
  title: string
  message: string
  priority: 'high' | 'medium' | 'low'
  timestamp: string
  isRead: boolean
  data?: any
}

// 시스템 상태 타입
export interface SystemStatus {
  service: string
  status: string
  message?: string
  timestamp?: string
}

// 폼 타입
export interface AddStockForm {
  code: string
  name: string
  purchase_price: number
  acquisition_price?: number
  quantity: number
  take_profit?: number
  stop_loss?: number
  daily_surge_threshold: number
  daily_drop_threshold: number
  alert_enabled: boolean
  
  // 메자닌 투자 관련
  category: 'mezzanine' | 'other'
  conversion_price?: number
  conversion_price_floor?: number
}

export interface UpdateStockForm {
  purchase_price?: number
  acquisition_price?: number
  quantity?: number
  take_profit?: number
  stop_loss?: number
  daily_surge_threshold?: number
  daily_drop_threshold?: number
  alert_enabled?: boolean
  
  // 메자닌 투자 관련
  category?: 'mezzanine' | 'other'
  conversion_price?: number
  conversion_price_floor?: number
}

// 검색 결과 타입
export interface StockSearchResult {
  code: string
  name: string
  market: string
  current_price?: number
  change_rate?: number
}

// 설정 타입
export interface DartSettings {
  check_interval: number
  keywords: DartKeyword[]
  companies: DartCompany[]
  email_enabled: boolean
  websocket_enabled: boolean
  report_types: string[]
}

export interface StockSettings {
  check_interval: number
  market_open: string
  market_close: string
  enable_email_alerts: boolean
  enable_websocket_alerts: boolean
  max_alerts_per_day: number
  retry_attempts: number
  timeout_seconds: number
}

// 유틸리티 타입
export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error'

export type AlertType = 'dart' | 'stock' | 'system'

export type MarketStatus = 'open' | 'closed' | 'pre_market' | 'after_market'

export type StockAlertType = 'take_profit' | 'stop_loss' | 'daily_surge' | 'daily_drop' | 'custom'

export type Priority = 'high' | 'medium' | 'low'