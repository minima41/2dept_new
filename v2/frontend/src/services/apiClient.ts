import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 응답 인터셉터
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const api = {
  // 시스템 API
  system: {
    health: () => apiClient.get('/health').then(res => res.data),
    status: () => apiClient.get('/api/system/status').then(res => res.data),
    diagnostics: () => apiClient.get('/api/system/diagnostics').then(res => res.data),
  },

  // DART API
  dart: {
    statistics: () => apiClient.get('/api/dart/statistics').then(res => res.data),
    disclosures: () => apiClient.get('/api/dart/disclosures').then(res => res.data),
    latest: () => apiClient.get('/api/dart/disclosures/latest').then(res => res.data),
    checkNow: () => apiClient.post('/api/dart/check-now').then(res => res.data),
  },

  // 주식 API
  stocks: {
    statistics: () => apiClient.get('/api/stocks/statistics').then(res => res.data),
    monitoring: () => apiClient.get('/api/stocks/monitoring').then(res => res.data),
    marketInfo: () => apiClient.get('/api/stocks/market-info').then(res => res.data),
    checkNow: () => apiClient.post('/api/stocks/update-prices').then(res => res.data),
    addStock: (stockData: any) => apiClient.post('/api/stocks/monitoring', stockData).then(res => res.data),
    updateStock: (code: string, stockData: any) => apiClient.put(`/api/stocks/monitoring/${code}`, stockData).then(res => res.data),
    removeStock: (code: string) => apiClient.delete(`/api/stocks/monitoring/${code}`).then(res => res.data),
  },

  // 알림 API
  notifications: {
    list: () => apiClient.get('/api/notifications/').then(res => res.data),
    unread: () => apiClient.get('/api/notifications/unread').then(res => res.data),
    markRead: (ids: string[]) => apiClient.post('/api/notifications/mark-read', { ids }).then(res => res.data),
    test: (type?: string) => apiClient.post(`/api/notifications/test?notification_type=${type || 'system'}`).then(res => res.data),
  },
}