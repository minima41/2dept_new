import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'

const API_BASE_URL = (import.meta as any).env.VITE_API_URL || 'http://localhost:8002'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // 요청 인터셉터
    this.client.interceptors.request.use(
      (config) => {
        // 토큰이 있다면 헤더에 추가
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // 응답 인터셉터
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // 토큰 만료 시 로그아웃 처리
          localStorage.removeItem('token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // 기본 HTTP 메서드들
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config)
    return response.data
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config)
    return response.data
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config)
    return response.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config)
    return response.data
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config)
    return response.data
  }
}

export const apiClient = new ApiClient()

// 편의 함수들
export const api = {
  // 기본 API
  health: () => apiClient.get<{ status: string }>('/health'),
  
  // DART API
  dart: {
    disclosures: (params?: { page?: number; page_size?: number; days?: number; keyword?: string; company?: string }) =>
      apiClient.get<any>('/api/dart/disclosures', { params }),
    
    keywords: () => apiClient.get<any>('/api/dart/keywords'),
    
    updateKeywords: (keywords: any[]) => apiClient.put<any>('/api/dart/keywords', keywords),
    
    companies: () => apiClient.get<any>('/api/dart/companies'),
    
    updateCompanies: (companies: any[]) => apiClient.put<any>('/api/dart/companies', companies),
    
    settings: () => apiClient.get<any>('/api/dart/settings'),
    
    alerts: (params?: { page?: number; page_size?: number; days?: number }) =>
      apiClient.get<any>('/api/dart/alerts', { params }),
    
    markAlertAsRead: (alertId: number) => apiClient.put<any>(`/api/dart/alerts/${alertId}/read`),
    
    statistics: () => apiClient.get<any>('/api/dart/statistics'),
    
    checkNow: () => apiClient.post<any>('/api/dart/check-now'),
    
    health: () => apiClient.get<any>('/api/dart/health'),
  },
  
  // 주가 API
  stocks: {
    price: (code: string) => apiClient.get<any>(`/api/stocks/prices/${code}`),
    
    prices: (codes: string[]) => apiClient.post<any>('/api/stocks/prices', { codes }),
    
    monitoring: () => apiClient.get<any>('/api/stocks/monitoring'),
    
    addMonitoring: (stock: any) => apiClient.post<any>('/api/stocks/monitoring', stock),
    
    updateMonitoring: (code: string, data: any) => apiClient.put<any>(`/api/stocks/monitoring/${code}`, data),
    
    removeMonitoring: (code: string) => apiClient.delete<any>(`/api/stocks/monitoring/${code}`),
    
    alerts: (params?: { page?: number; page_size?: number; days?: number }) =>
      apiClient.get<any>('/api/stocks/alerts', { params }),
    
    markAlertAsRead: (alertId: number) => apiClient.put<any>(`/api/stocks/alerts/${alertId}/read`),
    
    statistics: () => apiClient.get<any>('/api/stocks/statistics'),
    
    settings: () => apiClient.get<any>('/api/stocks/settings'),
    
    updateSettings: (settings: any) => apiClient.put<any>('/api/stocks/settings', settings),
    
    search: (query: string) => apiClient.get<any>('/api/stocks/search', { params: { q: query } }),
    
    marketInfo: () => apiClient.get<any>('/api/stocks/market-info'),
    
    checkNow: () => apiClient.post<any>('/api/stocks/check-now'),
    
    health: () => apiClient.get<any>('/api/stocks/health'),
  },
  
  // 포트폴리오 API (향후 구현)
  portfolio: {
    list: () => apiClient.get<any>('/api/portfolio'),
    create: (data: any) => apiClient.post<any>('/api/portfolio', data),
    update: (id: string, data: any) => apiClient.put<any>(`/api/portfolio/${id}`, data),
    delete: (id: string) => apiClient.delete<any>(`/api/portfolio/${id}`),
    statistics: () => apiClient.get<any>('/api/portfolio/statistics'),
  },
  
  // 로그 API
  logs: {
    recent: (count: number = 100) => apiClient.get<any>(`/api/logs/recent?count=${count}`),
    clear: () => apiClient.post<any>('/api/logs/clear'),
    test: (level: string = 'info', message: string = '테스트 로그 메시지') => 
      apiClient.post<any>(`/api/logs/test?level=${level}&message=${encodeURIComponent(message)}`),
  },
  
  // 이메일 API
  email: {
    testDailySummary: () => apiClient.post<any>('/api/email/test-daily-summary'),
  },
}

export default apiClient