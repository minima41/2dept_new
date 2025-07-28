/**
 * 투자본부 모니터링 시스템 v3 - 프론트엔드 JavaScript
 * Flask 백엔드 API와 연동하여 실시간 데이터 표시
 */

// 전역 변수
let currentStockTab = 'all';
let currentAlertFilter = 'all';
let currentMainTab = 'stocks'; // 메인 탭 (stocks, dart)
let currentStockCategory = 'all'; // 주식 카테고리 필터
let refreshInterval;
let logRefreshInterval;
let currentRefreshRate = 60; // 기본 60초

// API 기본 URL
const API_BASE = window.location.origin;

// DOM 요소들
const elements = {
    // 상태 표시
    dartStatus: document.getElementById('dart-status'),
    stockStatus: document.getElementById('stock-status'),
    systemUptime: document.getElementById('system-uptime'),
    
    // 메인 탭
    stockTab: document.getElementById('stock-tab'),
    dartTab: document.getElementById('dart-tab'),
    stocksContent: document.getElementById('stocks-content'),
    dartContent: document.getElementById('dart-content'),
    
    // 주식 관련
    stocksTable: document.getElementById('stocks-table'),
    stocksTableBody: document.getElementById('stocks-table-body'),
    loadingStocks: document.getElementById('loading-stocks'),
    noStocks: document.getElementById('no-stocks'),
    totalStocks: document.getElementById('total-stocks'),
    lastStockUpdate: document.getElementById('last-stock-update'),
    
    // 종목 관리
    addStock: document.getElementById('add-stock'),
    addFirstStock: document.getElementById('add-first-stock'),
    addCompany: document.getElementById('add-company'),
    addModal: document.getElementById('add-modal'),
    addModalTitle: document.getElementById('add-modal-title'),
    addModalClose: document.getElementById('add-modal-close'),
    addForm: document.getElementById('add-form'),
    addSubmit: document.getElementById('add-submit'),
    addCancel: document.getElementById('add-cancel'),
    stockFields: document.getElementById('stock-fields'),
    companyFields: document.getElementById('company-fields'),
    
    // 알림 관련
    alertsList: document.getElementById('alerts-list'),
    loadingAlerts: document.getElementById('loading-alerts'),
    noAlerts: document.getElementById('no-alerts'),
    dartAlertsToday: document.getElementById('dart-alerts-today'),
    stockAlertsToday: document.getElementById('stock-alerts-today'),
    stockAlertsToday2: document.getElementById('stock-alerts-today-2'),
    unreadAlerts: document.getElementById('unread-alerts'),
    
    // 모달
    modalOverlay: document.getElementById('modal-overlay'),
    modalTitle: document.getElementById('modal-title'),
    modalMessage: document.getElementById('modal-message'),
    modalClose: document.getElementById('modal-close'),
    modalOk: document.getElementById('modal-ok'),
    
    // 토스트
    toastContainer: document.getElementById('toast-container')
};

// 유틸리티 함수들
const utils = {
    // 숫자를 천 단위 콤마로 포맷
    formatNumber: (num) => {
        if (num === null || num === undefined) return '-';
        return parseInt(num).toLocaleString();
    },
    
    // 퍼센트 포맷 (색상 포함)
    formatPercent: (percent) => {
        if (percent === null || percent === undefined) return '-';
        const value = parseFloat(percent);
        const colorClass = value > 0 ? 'price-up' : value < 0 ? 'price-down' : 'price-unchanged';
        const sign = value > 0 ? '+' : '';
        return `<span class="${colorClass}">${sign}${value.toFixed(2)}%</span>`;
    },
    
    // 시간 포맷
    formatTime: (isoString) => {
        if (!isoString) return '-';
        const date = new Date(isoString);
        return date.toLocaleString('ko-KR');
    },
    
    // 시간차 계산
    formatTimeDiff: (isoString) => {
        if (!isoString) return '-';
        const now = new Date();
        const past = new Date(isoString);
        const diffMs = now - past;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return '방금 전';
        if (diffMins < 60) return `${diffMins}분 전`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}시간 전`;
        return `${Math.floor(diffMins / 1440)}일 전`;
    },
    
    // 가동 시간 포맷
    formatUptime: (seconds) => {
        if (!seconds) return '-';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}시간 ${minutes}분`;
    }
};

// 공통 에러 처리 함수들
const errorHandler = {
    // 표준 에러 응답 처리
    handleApiError(error, context = '') {
        console.error(`API 에러 ${context}:`, error);
        
        let userMessage = '알 수 없는 오류가 발생했습니다.';
        let errorCode = 'UNKNOWN_ERROR';
        
        if (error.response) {
            // HTTP 응답이 있는 경우
            const status = error.response.status;
            const data = error.response.data;
            
            switch (status) {
                case 400:
                    userMessage = '잘못된 요청입니다.';
                    errorCode = 'BAD_REQUEST';
                    break;
                case 404:
                    userMessage = '요청한 리소스를 찾을 수 없습니다.';
                    errorCode = 'NOT_FOUND';
                    break;
                case 500:
                    userMessage = '서버 내부 오류가 발생했습니다.';
                    errorCode = 'INTERNAL_ERROR';
                    break;
                default:
                    userMessage = `서버 오류 (${status})가 발생했습니다.`;
            }
            
            // 서버에서 제공한 에러 메시지가 있으면 사용
            if (data && data.error) {
                userMessage = data.error;
                errorCode = data.error_code || errorCode;
            }
        } else if (error.request) {
            // 네트워크 에러
            userMessage = '네트워크 연결을 확인해주세요.';
            errorCode = 'NETWORK_ERROR';
        } else {
            // 기타 에러
            userMessage = error.message || userMessage;
        }
        
        return {
            message: userMessage,
            code: errorCode,
            originalError: error
        };
    },
    
    // API 응답 검증
    validateApiResponse(response, context = '') {
        if (!response.ok) {
            const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
            error.response = {
                status: response.status,
                statusText: response.statusText
            };
            throw error;
        }
        return response;
    },
    
    // 표준 에러 표시
    showError(error, context = '') {
        const errorInfo = this.handleApiError(error, context);
        
        // 사용자에게 토스트 메시지 표시
        if (ui && ui.showToast) {
            ui.showToast(errorInfo.message, 'error');
        }
        
        // 개발 환경에서 상세 로깅
        console.group(`🚨 에러 상세 정보 ${context}`);
        console.error('에러 코드:', errorInfo.code);
        console.error('사용자 메시지:', errorInfo.message);
        console.error('원본 에러:', errorInfo.originalError);
        console.groupEnd();
        
        return errorInfo;
    }
};

// API 호출 함수들
const api = {
    // 시스템 상태 조회
    async getStatus() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/status`);
            errorHandler.validateApiResponse(response, '시스템 상태 조회');
            const data = await response.json();
            console.log('시스템 상태 조회 성공:', data);
            return data;
        } catch (error) {
            errorHandler.showError(error, '시스템 상태 조회');
            throw error;
        }
    },
    
    // 주식 목록 조회
    async getStocks() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks`);
            errorHandler.validateApiResponse(response, '주식 목록 조회');
            const data = await response.json();
            console.log('주식 목록 조회 성공:', data.success ? `${Object.keys(data.stocks || {}).length}개 종목` : '실패');
            return data;
        } catch (error) {
            errorHandler.showError(error, '주식 목록 조회');
            throw error;
        }
    },
    
    // 주식 수동 업데이트
    async updateStocks() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            console.log('주식 업데이트 성공:', data.message);
            return data;
        } catch (error) {
            console.error('주식 업데이트 실패:', error);
            throw error;
        }
    },
    
    // 알림 목록 조회
    async getAlerts(page = 1, type = 'all') {
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                limit: '20',
                type: type
            });
            const response = await fetch(`${API_BASE}/api/v1/alerts?${params}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            console.log('알림 목록 조회 성공:', data.success ? `${data.alerts?.length || 0}개 알림` : '실패');
            return data;
        } catch (error) {
            console.error('알림 목록 조회 실패:', error);
            throw error;
        }
    },
    
    // 일일 내역 조회
    async getDailyHistory() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/daily-history`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            console.log('일일 내역 조회 성공:', data.success ? `${data.data?.length || 0}개 내역` : '실패');
            return data;
        } catch (error) {
            console.error('일일 내역 조회 실패:', error);
            throw error;
        }
    },
    
    // DART 수동 확인
    async checkDart() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/dart/check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            console.log('DART 확인 성공:', data.message);
            return data;
        } catch (error) {
            console.error('DART 확인 실패:', error);
            throw error;
        }
    },
    
    // 이메일 테스트
    async testEmail() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/test/email`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    subject: '[테스트] D2 Dash 모니터링 시스템',
                    message: '이메일 발송 테스트입니다.'
                })
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            console.log('이메일 테스트 성공:', data.message);
            return data;
        } catch (error) {
            console.error('이메일 테스트 실패:', error);
            throw error;
        }
    },
    
    // 종목 추가
    async addStock(stockData) {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(stockData)
            });
            errorHandler.validateApiResponse(response, '종목 추가');
            const data = await response.json();
            console.log('종목 추가 성공:', data.message);
            return data;
        } catch (error) {
            errorHandler.showError(error, '종목 추가');
            throw error;
        }
    },

    // 메자닌 종목 추가 (전환가격 포함)
    async addMezzanineStock(stockData) {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/mezzanine`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(stockData)
            });
            errorHandler.validateApiResponse(response, '메자닌 종목 추가');
            const data = await response.json();
            console.log('메자닌 종목 추가 성공:', data.message);
            return data;
        } catch (error) {
            errorHandler.showError(error, '메자닌 종목 추가');
            throw error;
        }
    },

    // 카테고리별 주식 목록 조회
    async getStocksByCategory(category) {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/category/${category}`);
            errorHandler.validateApiResponse(response, '카테고리별 주식 조회');
            const data = await response.json();
            console.log(`카테고리 "${category}" 주식 조회 성공:`, data.success ? `${Object.keys(data.stocks || {}).length}개 종목` : '실패');
            return data;
        } catch (error) {
            errorHandler.showError(error, '카테고리별 주식 조회');
            throw error;
        }
    },

    // 카테고리 목록 조회
    async getCategories() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/categories`);
            errorHandler.validateApiResponse(response, '카테고리 목록 조회');
            const data = await response.json();
            console.log('카테고리 목록 조회 성공:', data.categories?.length || 0, '개');
            return data;
        } catch (error) {
            errorHandler.showError(error, '카테고리 목록 조회');
            throw error;
        }
    },

    // 카테고리 마이그레이션 (관리자 전용)
    async migrateCategories() {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/migrate-categories`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            errorHandler.validateApiResponse(response, '카테고리 마이그레이션');
            const data = await response.json();
            console.log('카테고리 마이그레이션 성공:', data.message);
            return data;
        } catch (error) {
            errorHandler.showError(error, '카테고리 마이그레이션');
            throw error;
        }
    },
    
    // 종목 삭제
    async deleteStock(stockCode) {
        try {
            const response = await fetch(`${API_BASE}/api/v1/stocks/${stockCode}`, {
                method: 'DELETE'
            });
            errorHandler.validateApiResponse(response, '종목 삭제');
            const data = await response.json();
            console.log('종목 삭제 성공:', data.message);
            return data;
        } catch (error) {
            errorHandler.showError(error, '종목 삭제');
            throw error;
        }
    },
    
    // 기업 추가
    async addCompany(companyData) {
        try {
            const response = await fetch(`${API_BASE}/api/v1/dart/companies`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(companyData)
            });
            errorHandler.validateApiResponse(response, '기업 추가');
            const data = await response.json();
            console.log('기업 추가 성공:', data.message);
            return data;
        } catch (error) {
            errorHandler.showError(error, '기업 추가');
            throw error;
        }
    },
    
    // 기업 삭제
    async deleteCompany(companyCode) {
        try {
            const response = await fetch(`${API_BASE}/api/v1/dart/companies/${companyCode}`, {
                method: 'DELETE'
            });
            errorHandler.validateApiResponse(response, '기업 삭제');
            const data = await response.json();
            console.log('기업 삭제 성공:', data.message);
            return data;
        } catch (error) {
            errorHandler.showError(error, '기업 삭제');
            throw error;
        }
    }
};

// UI 업데이트 함수들
const ui = {
    // 시스템 상태 업데이트
    updateSystemStatus(data) {
        // DART 모니터링 상태
        const dartEnabled = data.dart_monitoring?.enabled;
        elements.dartStatus.className = `status-indicator ${dartEnabled ? 'active' : 'inactive'}`;
        elements.dartStatus.innerHTML = `<i class="fas fa-circle"></i> ${dartEnabled ? '활성' : '비활성'}`;
        
        // 주식 모니터링 상태
        const stockEnabled = data.stock_monitoring?.enabled;
        elements.stockStatus.className = `status-indicator ${stockEnabled ? 'active' : 'inactive'}`;
        elements.stockStatus.innerHTML = `<i class="fas fa-circle"></i> ${stockEnabled ? '활성' : '비활성'}`;
        
        // 가동 시간
        if (elements.systemUptime) {
            elements.systemUptime.textContent = utils.formatUptime(data.system?.uptime_seconds);
        }
        
        // 통계 업데이트
        if (elements.dartAlertsToday) {
            elements.dartAlertsToday.textContent = data.dart_monitoring?.alerts_today || 0;
        }
        if (elements.stockAlertsToday) {
            elements.stockAlertsToday.textContent = data.stock_monitoring?.alerts_today || 0;
        }
        if (elements.stockAlertsToday2) {
            elements.stockAlertsToday2.textContent = data.stock_monitoring?.alerts_today || 0;
        }
        if (elements.totalStocks) {
            elements.totalStocks.textContent = data.monitoring_stocks_count || 0;
        }
        if (elements.lastStockUpdate) {
            elements.lastStockUpdate.textContent = utils.formatTimeDiff(data.stock_monitoring?.last_update);
        }
    },
    
    // 주식 테이블 업데이트
    updateStockTable(data) {
        if (!data.success || !data.stocks) {
            this.showEmptyStocks();
            return;
        }
        
        const stocks = Object.entries(data.stocks);
        
        if (stocks.length === 0) {
            this.showEmptyStocks();
            return;
        }
        
        // 현재 카테고리에 따른 필터링
        const filteredStocks = stocks.filter(([code, info]) => {
            if (currentStockCategory === 'all') return true;
            if (currentStockCategory === '메자닌') return info.category === '메자닌';
            if (currentStockCategory === '주식') return info.category === '주식' || info.category === '기타';
            if (currentStockCategory === '기타') return info.category === '기타';
            return true;
        });
        
        // 테이블 헤더 동적 변경
        this.updateTableHeaders();
        
        // 테이블 body 생성
        elements.stocksTableBody.innerHTML = '';
        
        filteredStocks.forEach(([code, info]) => {
            const row = document.createElement('tr');
            row.className = info.enabled ? '' : 'disabled';
            
            const category = info.category || '주식';
            const currentPrice = utils.formatNumber(info.current_price);
            const changePercent = utils.formatPercent(info.change_percent);
            const targetPrice = utils.formatNumber(info.target_price);
            const stopLoss = utils.formatNumber(info.stop_loss);
            const lastUpdated = utils.formatTimeDiff(info.last_updated);
            const status = info.error ? 
                `<span class="status-error"><i class="fas fa-exclamation-triangle"></i> 오류</span>` :
                info.current_price > 0 ? 
                `<span class="status-active"><i class="fas fa-check-circle"></i> 정상</span>` :
                `<span class="status-inactive"><i class="fas fa-clock"></i> 대기</span>`;
            
            // 메자닌인 경우 패리티 컬럼 추가
            let extraColumns = '';
            if (currentStockCategory === '메자닌' || (currentStockCategory === 'all' && category === '메자닌')) {
                const conversionPrice = info.conversion_price || info.current_price;
                const parity = conversionPrice && info.current_price ? 
                    ((info.current_price / conversionPrice) * 100).toFixed(1) + '%' : '-';
                extraColumns = `<td>${parity}</td>`;
            }
            
            // 알림 설정 상태 확인
            const alertSettings = info.alert_settings || {};
            const alertEnabled = alertSettings.alert_enabled !== false; // 기본값 true
            
            row.innerHTML = `
                <td><code>${code}</code></td>
                <td><strong>${info.name || code}</strong></td>
                <td><span class="category-badge category-${category === '메자닌' ? 'mezzanine' : 'others'}">${category}</span></td>
                <td class="text-right price-cell" data-price="${info.current_price || 0}">${currentPrice}</td>
                <td class="text-right">${changePercent}</td>
                ${extraColumns}
                <td class="text-right">${targetPrice}</td>
                <td class="text-right">${stopLoss}</td>
                <td class="text-center">${lastUpdated}</td>
                <td class="text-center">${status}</td>
                <td class="text-center">
                    <label class="alarm-toggle">
                        <input type="checkbox" ${alertEnabled ? 'checked' : ''} 
                               onchange="toggleStockAlert('${code}', this.checked)">
                        <span class="alarm-slider"></span>
                    </label>
                </td>
                <td class="text-center">
                    <button class="btn btn-sm btn-danger delete-stock-btn" data-stock-code="${code}" data-stock-name="${info.name || code}">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            
            elements.stocksTableBody.appendChild(row);
        });
        
        // 테이블 표시
        elements.loadingStocks.style.display = 'none';
        elements.noStocks.style.display = 'none';
        elements.stocksTable.style.display = 'table';
        
        // 서브 탭 카운트 업데이트
        updateSubTabCounts();
    },
    
    // 테이블 헤더 업데이트
    updateTableHeaders() {
        const thead = elements.stocksTable.querySelector('thead tr');
        
        if (currentStockCategory === '메자닌') {
            thead.innerHTML = `
                <th>종목코드</th>
                <th>종목명</th>
                <th>구분</th>
                <th>현재가</th>
                <th>등락률</th>
                <th>패리티(%)</th>
                <th>목표가(TP)</th>
                <th>손절가(SL)</th>
                <th>마지막체크</th>
                <th>상태</th>
                <th>알람설정</th>
                <th>관리</th>
            `;
        } else {
            thead.innerHTML = `
                <th>종목코드</th>
                <th>종목명</th>
                <th>구분</th>
                <th>현재가</th>
                <th>등락률</th>
                <th>목표가(TP)</th>
                <th>손절가(SL)</th>
                <th>마지막체크</th>
                <th>상태</th>
                <th>알람설정</th>
                <th>관리</th>
            `;
        }
    },
    
    // 빈 주식 목록 표시
    showEmptyStocks() {
        elements.loadingStocks.style.display = 'none';
        elements.stocksTable.style.display = 'none';
        elements.noStocks.style.display = 'block';
    },
    
    // 알림 목록 업데이트
    updateAlertsList(data) {
        if (!data.success || !data.alerts) {
            this.showEmptyAlerts();
            return;
        }
        
        const alerts = data.alerts;
        
        if (alerts.length === 0) {
            this.showEmptyAlerts();
            return;
        }
        
        elements.alertsList.innerHTML = '';
        
        alerts.forEach(alert => {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert-item ${alert.type} ${alert.read ? 'read' : 'unread'}`;
            
            const iconClass = alert.type === 'dart' ? 'fas fa-file-alt' : 'fas fa-chart-line';
            const priorityClass = alert.priority >= 50 ? 'high' : alert.priority >= 20 ? 'medium' : 'low';
            
            alertDiv.innerHTML = `
                <div class="alert-icon">
                    <i class="${iconClass}"></i>
                </div>
                <div class="alert-content">
                    <div class="alert-header">
                        <span class="alert-title">${alert.title}</span>
                        <span class="alert-priority priority-${priorityClass}">${alert.priority}점</span>
                        <span class="alert-time">${utils.formatTimeDiff(alert.timestamp)}</span>
                    </div>
                    <div class="alert-message">${alert.message}</div>
                </div>
                <div class="alert-actions">
                    ${!alert.read ? `<button class="btn-mark-read" data-id="${alert.id}"><i class="fas fa-check"></i></button>` : ''}
                </div>
            `;
            
            elements.alertsList.appendChild(alertDiv);
        });
        
        // 읽음 처리 버튼 이벤트
        elements.alertsList.querySelectorAll('.btn-mark-read').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const alertId = e.target.closest('.btn-mark-read').dataset.id;
                await this.markAlertRead(alertId);
            });
        });
        
        // 미읽은 알림 수 업데이트
        const unreadCount = alerts.filter(alert => !alert.read).length;
        if (elements.unreadAlerts) {
            elements.unreadAlerts.textContent = unreadCount;
        }
        
        // 알림 목록 표시
        elements.loadingAlerts.style.display = 'none';
        elements.noAlerts.style.display = 'none';
        elements.alertsList.style.display = 'block';
    },
    
    // 빈 알림 목록 표시
    showEmptyAlerts() {
        elements.loadingAlerts.style.display = 'none';
        elements.alertsList.style.display = 'none';
        elements.noAlerts.style.display = 'block';
    },
    
    // 알림 읽음 처리
    async markAlertRead(alertId) {
        try {
            const response = await fetch(`${API_BASE}/api/v1/alerts/${alertId}/read`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('알림 읽음 처리 성공:', data.message);
            
            // 해당 알림 아이템을 읽음으로 표시
            const alertItem = document.querySelector(`[data-id="${alertId}"]`).closest('.alert-item');
            if (alertItem) {
                alertItem.classList.remove('unread');
                alertItem.classList.add('read');
                const readBtn = alertItem.querySelector('.btn-mark-read');
                if (readBtn) {
                    readBtn.remove();
                }
            }
            
            this.showToast('알림을 읽음으로 처리했습니다.', 'success');
            
        } catch (error) {
            console.error('알림 읽음 처리 실패:', error);
            this.showToast(`알림 처리에 실패했습니다: ${error.message}`, 'error');
        }
    },
    
    // 모달 표시
    showModal(title, message) {
        elements.modalTitle.textContent = title;
        elements.modalMessage.textContent = message;
        elements.modalOverlay.style.display = 'flex';
    },
    
    // 모달 숨김
    hideModal() {
        elements.modalOverlay.style.display = 'none';
    },
    
    // 토스트 알림 표시
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const iconClass = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        }[type] || 'fas fa-info-circle';
        
        toast.innerHTML = `
            <i class="${iconClass}"></i>
            <span>${message}</span>
            <button class="toast-close"><i class="fas fa-times"></i></button>
        `;
        
        elements.toastContainer.appendChild(toast);
        
        // 자동 제거
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);
        
        // 수동 닫기
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        });
    },
    
    // 일일 내역 업데이트
    updateDailyHistory(data) {
        const loadingElement = document.getElementById('loading-daily-history');
        const containerElement = document.getElementById('daily-history-container');
        const noDataElement = document.getElementById('no-daily-history');
        const tbody = document.getElementById('daily-history-body');
        
        loadingElement.style.display = 'none';
        
        if (!data || data.length === 0) {
            containerElement.style.display = 'none';
            noDataElement.style.display = 'block';
            return;
        }
        
        // 테이블 행 생성
        tbody.innerHTML = data.map(item => {
            const alertTypeClass = this.getAlertTypeClass(item.alert_type);
            const timeStr = new Date(item.timestamp).toLocaleTimeString('ko-KR');
            
            return `
                <tr>
                    <td>${timeStr}</td>
                    <td>${item.stock_code || '-'}</td>
                    <td>${item.stock_name || '-'}</td>
                    <td>${item.action || '-'}</td>
                    <td><span class="alert-type ${alertTypeClass}">${item.alert_type || '-'}</span></td>
                    <td>${item.current_price ? `${parseInt(item.current_price).toLocaleString()}원` : '-'}</td>
                    <td>${item.reference_price ? `${parseInt(item.reference_price).toLocaleString()}원` : '-'}</td>
                </tr>
            `;
        }).join('');
        
        containerElement.style.display = 'block';
        noDataElement.style.display = 'none';
    },
    
    // 빈 일일 내역 표시
    showEmptyDailyHistory() {
        const loadingElement = document.getElementById('loading-daily-history');
        const containerElement = document.getElementById('daily-history-container');
        const noDataElement = document.getElementById('no-daily-history');
        
        loadingElement.style.display = 'none';
        containerElement.style.display = 'none';
        noDataElement.style.display = 'block';
    },
    
    // 실시간 로그 추가
    addLog(message, type = 'info') {
        const logsContainer = document.getElementById('logs-container');
        if (!logsContainer) return;
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        
        const currentTime = new Date().toLocaleTimeString('ko-KR');
        logEntry.innerHTML = `
            <span class="log-time">[${currentTime}]</span>
            <span class="log-message">${message}</span>
        `;
        
        logsContainer.appendChild(logEntry);
        
        // 자동 스크롤
        logsContainer.scrollTop = logsContainer.scrollHeight;
        
        // 로그가 너무 많아지면 오래된 것부터 제거 (최대 100개)
        const maxLogs = 100;
        const logEntries = logsContainer.querySelectorAll('.log-entry');
        if (logEntries.length > maxLogs) {
            logEntries[0].remove();
        }
    },
    
    // 로그 초기화
    clearLogs() {
        const logsContainer = document.getElementById('logs-container');
        if (logsContainer) {
            logsContainer.innerHTML = '';
            this.addLog('로그가 초기화되었습니다.', 'info');
        }
    },
    
    // 알림 타입에 따른 CSS 클래스 반환
    getAlertTypeClass(alertType) {
        const classMap = {
            'target_price': 'success',
            'stop_loss': 'danger',
            'surge': 'warning',
            'drop': 'danger',
            'parity': 'info'
        };
        return classMap[alertType] || 'secondary';
    }
};

// 데이터 로딩 함수들
const dataLoader = {
    // 시스템 상태 로드
    async loadSystemStatus() {
        try {
            console.log('시스템 상태 로드 시작...');
            const data = await api.getStatus();
            ui.updateSystemStatus(data);
            console.log('시스템 상태 로드 완료');
        } catch (error) {
            // 시스템 상태는 에러 로깅만 하고 토스트는 표시하지 않음 (너무 빈번할 수 있음)
            errorHandler.handleApiError(error, '시스템 상태 로드');
            
            // 상태 표시를 오류로 설정
            if (elements.dartStatus) {
                elements.dartStatus.className = 'status-indicator error';
                elements.dartStatus.innerHTML = '<i class="fas fa-circle"></i> 연결 오류';
            }
            if (elements.stockStatus) {
                elements.stockStatus.className = 'status-indicator error';
                elements.stockStatus.innerHTML = '<i class="fas fa-circle"></i> 연결 오류';
            }
        }
    },
    
    // 주식 데이터 로드
    async loadStocks() {
        try {
            console.log('주식 데이터 로드 시작...');
            elements.loadingStocks.style.display = 'block';
            elements.stocksTable.style.display = 'none';
            elements.noStocks.style.display = 'none';
            
            const data = await api.getStocks();
            
            if (!data || !data.success) {
                throw new Error(data?.error || '주식 데이터 로드 실패');
            }
            
            ui.updateStockTable(data);
            console.log('주식 데이터 로드 완료');
            
        } catch (error) {
            console.error('주식 데이터 로드 실패:', error);
            ui.showEmptyStocks();
            ui.showToast(`주식 데이터 로드 실패: ${error.message}`, 'error');
        }
    },
    
    // 알림 데이터 로드
    async loadAlerts() {
        try {
            console.log(`알림 데이터 로드 시작... (필터: ${currentAlertFilter})`);
            elements.loadingAlerts.style.display = 'block';
            elements.alertsList.style.display = 'none';
            elements.noAlerts.style.display = 'none';
            
            const data = await api.getAlerts(1, currentAlertFilter);
            
            if (!data || !data.success) {
                throw new Error(data?.error || '알림 데이터 로드 실패');
            }
            
            ui.updateAlertsList(data);
            console.log('알림 데이터 로드 완료');
            
        } catch (error) {
            console.error('알림 데이터 로드 실패:', error);
            ui.showEmptyAlerts();
            ui.showToast(`알림 데이터 로드 실패: ${error.message}`, 'error');
        }
    },
    
    // 일일 내역 로드
    async loadDailyHistory() {
        try {
            console.log('일일 내역 로드 시작...');
            const loadingElement = document.getElementById('loading-daily-history');
            const containerElement = document.getElementById('daily-history-container');
            const noDataElement = document.getElementById('no-daily-history');
            
            loadingElement.style.display = 'block';
            containerElement.style.display = 'none';
            noDataElement.style.display = 'none';
            
            const data = await api.getDailyHistory();
            
            if (!data || !data.success) {
                throw new Error(data?.error || '일일 내역 로드 실패');
            }
            
            ui.updateDailyHistory(data.data || []);
            console.log('일일 내역 로드 완료');
            
        } catch (error) {
            console.error('일일 내역 로드 실패:', error);
            ui.showEmptyDailyHistory();
            ui.showToast(`일일 내역 로드 실패: ${error.message}`, 'error');
        }
    },
    
    // 모든 데이터 로드
    async loadAllData() {
        console.log('전체 데이터 로드 시작...');
        
        // 병렬로 로드하되 실패해도 다른 작업은 계속 진행
        const results = await Promise.allSettled([
            this.loadSystemStatus(),
            this.loadStocks(),
            this.loadAlerts(),
            this.loadDailyHistory()
        ]);
        
        // 실패한 작업 수 계산
        const failedCount = results.filter(result => result.status === 'rejected').length;
        
        if (failedCount > 0) {
            console.warn(`전체 데이터 로드 완료: ${4 - failedCount}/4 성공`);
        } else {
            console.log('전체 데이터 로드 완료: 모든 작업 성공');
        }
    }
};

// 이벤트 핸들러들
const eventHandlers = {
    // 주식 탭 변경
    handleStockTabChange(tab) {
        currentStockTab = tab;
        
        // 탭 버튼 활성화 상태 변경
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
        
        // 테이블 다시 로드
        dataLoader.loadStocks();
    },
    
    // 알림 필터 변경
    handleAlertFilterChange(filter) {
        currentAlertFilter = filter;
        
        // 필터 버튼 활성화 상태 변경
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
        
        // 알림 목록 다시 로드
        dataLoader.loadAlerts();
    },
    
    // 주식 수동 업데이트
    async handleManualStockUpdate() {
        try {
            console.log('주식 수동 업데이트 시작...');
            ui.showToast('주식 가격을 업데이트하고 있습니다...', 'info');
            
            const result = await api.updateStocks();
            
            if (!result || !result.success) {
                throw new Error(result?.error || '주식 업데이트 실패');
            }
            
            ui.showToast(result.message || '주식 가격 업데이트 완료', 'success');
            
            // 업데이트 후 데이터 다시 로드
            await dataLoader.loadStocks();
            await dataLoader.loadSystemStatus(); // 시스템 상태도 업데이트
            
            console.log('주식 수동 업데이트 완료');
            
        } catch (error) {
            console.error('주식 수동 업데이트 실패:', error);
            ui.showToast(`주식 업데이트 실패: ${error.message}`, 'error');
        }
    },
    
    // DART 수동 확인
    async handleManualDartCheck() {
        try {
            console.log('DART 수동 확인 시작...');
            ui.showToast('DART 공시를 확인하고 있습니다...', 'info');
            
            const result = await api.checkDart();
            
            if (!result || !result.success) {
                throw new Error(result?.error || 'DART 확인 실패');
            }
            
            const newDisclosuresCount = result.new_disclosures || result.disclosures?.length || 0;
            const message = newDisclosuresCount > 0 ? 
                `새로운 공시 ${newDisclosuresCount}건을 발견했습니다.` :
                '새로운 공시가 없습니다.';
            
            ui.showToast(message, 'success');
            
            // 새로운 공시가 있으면 알림 목록도 새로고침
            if (newDisclosuresCount > 0) {
                await dataLoader.loadAlerts();
                await dataLoader.loadSystemStatus(); // 시스템 상태도 업데이트
            }
            
            console.log(`DART 수동 확인 완료: ${newDisclosuresCount}건 발견`);
            
        } catch (error) {
            console.error('DART 수동 확인 실패:', error);
            ui.showToast(`DART 확인 실패: ${error.message}`, 'error');
        }
    },
    
    // 이메일 테스트
    async handleEmailTest() {
        try {
            console.log('이메일 테스트 시작...');
            ui.showToast('테스트 이메일을 발송하고 있습니다...', 'info');
            
            const result = await api.testEmail();
            
            if (!result || !result.success) {
                throw new Error(result?.error || '이메일 발송 실패');
            }
            
            ui.showToast(result.message || '테스트 이메일이 발송되었습니다.', 'success');
            console.log('이메일 테스트 완료');
            
        } catch (error) {
            console.error('이메일 테스트 실패:', error);
            ui.showToast(`이메일 테스트 실패: ${error.message}`, 'error');
        }
    }
};

// 초기화 함수
function init() {
    console.log('D2 Dash 모니터링 시스템 v3 초기화 시작');
    
    try {
        // 이벤트 리스너 설정
        setupEventListeners();
        
        // 초기 데이터 로드
        dataLoader.loadAllData().then(() => {
            console.log('초기 데이터 로드 완료');
        }).catch(error => {
            console.error('초기 데이터 로드 중 오류:', error);
            ui.showToast('초기 데이터 로드 중 일부 오류가 발생했습니다.', 'warning');
        });
        
        // 자동 새로고침 설정 (30초마다)
        refreshInterval = setInterval(() => {
            console.log('자동 새로고침 실행...');
            ui.addLog('시스템 자동 새로고침 시작', 'info');
            Promise.allSettled([
                dataLoader.loadSystemStatus(),
                dataLoader.loadStocks(),
                dataLoader.loadAlerts()
            ]).then(results => {
                const failedCount = results.filter(r => r.status === 'rejected').length;
                if (failedCount > 0) {
                    console.warn(`자동 새로고침 완료: ${3 - failedCount}/3 성공`);
                    ui.addLog(`자동 새로고침 완료: ${3 - failedCount}/3 성공`, 'warning');
                } else {
                    ui.addLog('자동 새로고침 완료: 모든 데이터 갱신 성공', 'success');
                }
            });
        }, 30000);
        
        // 로그 새로고침 주기 설정
        setupLogRefreshInterval();
        
        // 초기 로그 메시지
        ui.addLog('D2 Dash 모니터링 시스템 v3 시작', 'success');
        
        console.log('D2 Dash 초기화 완료');
        
    } catch (error) {
        console.error('초기화 중 오류:', error);
        ui.showToast('시스템 초기화 중 오류가 발생했습니다.', 'error');
    }
}

// 로그 새로고침 주기 설정 함수
function setupLogRefreshInterval() {
    // 기존 인터벌 제거
    if (logRefreshInterval) {
        clearInterval(logRefreshInterval);
    }
    
    // 새로운 인터벌 설정
    logRefreshInterval = setInterval(() => {
        ui.addLog(`자동 새로고침 실행 (${currentRefreshRate}초 주기)`, 'info');
        dataLoader.loadDailyHistory();
    }, currentRefreshRate * 1000);
    
    console.log(`로그 새로고침 주기 설정: ${currentRefreshRate}초`);
}

// 이벤트 리스너 설정 함수
function setupEventListeners() {
    // 탭 버튼 이벤트 연결
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            if (tab) {
                eventHandlers.handleStockTabChange(tab);
            }
        });
    });
    
    // 알림 필터 버튼 이벤트 연결
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const filter = e.target.dataset.filter;
            if (filter) {
                eventHandlers.handleAlertFilterChange(filter);
            }
        });
    });
    
    // 새로고침 버튼들
    document.getElementById('refresh-stocks')?.addEventListener('click', () => {
        console.log('주식 수동 새로고침 실행');
        dataLoader.loadStocks();
    });
    
    document.getElementById('refresh-alerts')?.addEventListener('click', () => {
        console.log('알림 수동 새로고침 실행');
        dataLoader.loadAlerts();
    });
    
    // 수동 업데이트 버튼
    document.getElementById('manual-update')?.addEventListener('click', () => {
        eventHandlers.handleManualStockUpdate();
    });
    
    // DART 수동 확인 버튼
    document.getElementById('dart-manual-check')?.addEventListener('click', () => {
        eventHandlers.handleManualDartCheck();
    });
    
    // 이메일 테스트 버튼
    document.getElementById('test-email')?.addEventListener('click', () => {
        eventHandlers.handleEmailTest();
    });
    
    // 모달 관련 이벤트
    elements.modalClose?.addEventListener('click', () => {
        ui.hideModal();
    });
    
    elements.modalOk?.addEventListener('click', () => {
        ui.hideModal();
    });
    
    elements.modalOverlay?.addEventListener('click', (e) => {
        if (e.target === elements.modalOverlay) {
            ui.hideModal();
        }
    });
    
    // 메인 탭 전환 이벤트
    elements.stockTab?.addEventListener('click', () => {
        switchMainTab('stocks');
    });
    
    elements.dartTab?.addEventListener('click', () => {
        switchMainTab('dart');
    });
    
    // 카테고리 필터 이벤트
    // 서브 탭 이벤트 리스너
    document.querySelectorAll('.sub-tab[data-category]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const category = e.target.closest('.sub-tab').dataset.category;
            if (category) {
                switchStockCategory(category);
            }
        });
    });
    
    // 종목/기업 추가 버튼 이벤트
    elements.addStock?.addEventListener('click', () => {
        openAddModal('stock');
    });
    
    elements.addFirstStock?.addEventListener('click', () => {
        openAddModal('stock');
    });
    
    elements.addCompany?.addEventListener('click', () => {
        openAddModal('company');
    });

    // 종목 카테고리 선택 시 메자닌 필드 표시/숨김
    document.getElementById('stock-category')?.addEventListener('change', (e) => {
        const mezzanineFields = document.getElementById('mezzanine-fields');
        const conversionPriceInput = document.getElementById('conversion-price');
        
        if (e.target.value === '메자닌') {
            mezzanineFields.style.display = 'block';
            conversionPriceInput.required = true;
        } else {
            mezzanineFields.style.display = 'none';
            conversionPriceInput.required = false;
            conversionPriceInput.value = '';
        }
    });
    
    // 추가 모달 이벤트
    elements.addModalClose?.addEventListener('click', () => {
        closeAddModal();
    });
    
    elements.addCancel?.addEventListener('click', () => {
        closeAddModal();
    });
    
    elements.addSubmit?.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        handleAddSubmit();
    });
    
    elements.addModal?.addEventListener('click', (e) => {
        if (e.target === elements.addModal) {
            closeAddModal();
        }
    });
    
    // 급등급락 알림 체크박스 토글 이벤트
    document.getElementById('volatility-alert-enabled')?.addEventListener('change', (e) => {
        const thresholdFields = document.getElementById('threshold-fields');
        if (thresholdFields) {
            thresholdFields.style.display = e.target.checked ? 'block' : 'none';
        }
    });
    
    // 삭제 버튼 이벤트 (이벤트 위임 사용)
    document.addEventListener('click', async (e) => {
        if (e.target.closest('.delete-stock-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const btn = e.target.closest('.delete-stock-btn');
            const stockCode = btn.dataset.stockCode;
            const stockName = btn.dataset.stockName;
            
            if (confirm(`정말로 "${stockName}(${stockCode})" 종목을 삭제하시겠습니까?`)) {
                try {
                    const response = await api.deleteStock(stockCode);
                    if (response.success) {
                        ui.showToast(`${stockName} 종목이 삭제되었습니다.`, 'success');
                        dataLoader.loadStocks(); // 목록 새로고침
                    } else {
                        ui.showToast(`종목 삭제 실패: ${response.error}`, 'error');
                    }
                } catch (error) {
                    ui.showToast(`종목 삭제 중 오류 발생: ${error.message}`, 'error');
                }
            }
        }
    });
    
    // 하단 패널 관련 이벤트
    // 일일 내역 새로고침 버튼
    document.getElementById('refresh-daily-history')?.addEventListener('click', () => {
        ui.addLog('일일 내역 새로고침 요청', 'info');
        dataLoader.loadDailyHistory();
    });
    
    // 새로고침 주기 변경
    document.getElementById('refresh-interval')?.addEventListener('change', (e) => {
        const newInterval = parseInt(e.target.value);
        currentRefreshRate = newInterval;
        setupLogRefreshInterval();
        ui.addLog(`새로고침 주기가 ${newInterval}초로 변경되었습니다.`, 'success');
    });
    
    // 로그 지우기 버튼
    document.getElementById('clear-logs')?.addEventListener('click', () => {
        ui.clearLogs();
    });
    
    console.log('이벤트 리스너 설정 완료');
}

// SPA 탭 전환 함수
function switchMainTab(tab) {
    console.log(`메인 탭 전환: ${tab}`);
    
    // 탭 버튼 활성화 상태 변경
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    if (tab === 'stocks') {
        elements.stockTab?.classList.add('active');
        elements.stocksContent?.style.setProperty('display', 'block');
        elements.dartContent?.style.setProperty('display', 'none');
    } else if (tab === 'dart') {
        elements.dartTab?.classList.add('active');
        elements.stocksContent?.style.setProperty('display', 'none');
        elements.dartContent?.style.setProperty('display', 'block');
        
        // DART 탭으로 전환 시 DART 데이터 로드
        if (typeof dartManager !== 'undefined' && dartManager.initialize) {
            dartManager.initialize();
        }
    }
    
    currentMainTab = tab;
}

// 주식 카테고리 필터 전환
function switchStockCategory(category) {
    console.log(`주식 카테고리 필터 전환: ${category}`);
    
    // 서브 탭 활성화 상태 변경
    document.querySelectorAll('.sub-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.querySelector(`.sub-tab[data-category="${category}"]`)?.classList.add('active');
    
    currentStockCategory = category;
    
    // 주식 테이블 필터링
    filterStockTable(category);
}

// 주식 테이블 필터링
function filterStockTable(category) {
    const tableBody = elements.stocksTableBody;
    if (!tableBody) return;
    
    const rows = tableBody.querySelectorAll('tr');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const categoryCell = row.querySelector('td:nth-child(3)'); // 구분 컬럼
        if (!categoryCell) return;
        
        const rowCategory = categoryCell.textContent.trim();
        
        if (category === 'all' || rowCategory === category) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // 서브 탭 카운트 업데이트
    updateSubTabCounts();
    
    console.log(`주식 필터링 완료: ${category} - ${visibleCount}개 표시`);
}

// 서브 탭 카운트 업데이트
function updateSubTabCounts() {
    const tableBody = elements.stocksTableBody;
    if (!tableBody) return;
    
    const rows = tableBody.querySelectorAll('tr');
    let allCount = 0;
    let mezzanineCount = 0;
    let stockCount = 0;
    
    rows.forEach(row => {
        const categoryCell = row.querySelector('td:nth-child(3)'); // 구분 컬럼
        if (!categoryCell) return;
        
        const rowCategory = categoryCell.textContent.trim();
        allCount++;
        
        if (rowCategory === '메자닌') {
            mezzanineCount++;
        } else if (rowCategory === '주식' || rowCategory === '기타') {
            stockCount++;
        }
    });
    
    // 카운트 업데이트
    const countAll = document.getElementById('count-all');
    const countMezzanine = document.getElementById('count-mezzanine');
    const countStock = document.getElementById('count-stock');
    
    if (countAll) countAll.textContent = allCount;
    if (countMezzanine) countMezzanine.textContent = mezzanineCount;
    if (countStock) countStock.textContent = stockCount;
}

// 주식 알림 토글
async function toggleStockAlert(stockCode, enabled) {
    try {
        console.log(`주식 알림 토글: ${stockCode} - ${enabled ? '활성화' : '비활성화'}`);
        
        const response = await fetch(`${API_BASE}/api/v1/stocks/${stockCode}/alert`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                alert_enabled: enabled
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`${stockCode} 알림이 ${enabled ? '활성화' : '비활성화'}되었습니다.`, 'success');
        } else {
            showToast(`알림 설정 변경 실패: ${data.message}`, 'error');
            // 토글 상태 되돌리기
            const checkbox = document.querySelector(`input[onchange*="${stockCode}"]`);
            if (checkbox) checkbox.checked = !enabled;
        }
        
    } catch (error) {
        console.error('알림 토글 오류:', error);
        showToast('알림 설정 변경 중 오류가 발생했습니다.', 'error');
        // 토글 상태 되돌리기
        const checkbox = document.querySelector(`input[onchange*="${stockCode}"]`);
        if (checkbox) checkbox.checked = !enabled;
    }
}

// 가격 변경 하이라이트 효과
function highlightPriceChange(stockCode, newPrice, oldPrice) {
    if (!newPrice || !oldPrice || newPrice === oldPrice) return;
    
    // 해당 종목의 가격 셀 찾기
    const priceCell = document.querySelector(`[data-price][data-stock-code="${stockCode}"]`);
    if (!priceCell) return;
    
    // 하이라이트 효과 적용
    priceCell.classList.add('price-highlight');
    
    // 1초 후 클래스 제거
    setTimeout(() => {
        priceCell.classList.remove('price-highlight');
    }, 1000);
}

// 실시간 업데이트 개선 (기존 함수 확장)
function startRealTimeUpdates() {
    // 기존 인터벌 정리
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    // 10초 간격으로 업데이트
    refreshInterval = setInterval(async () => {
        if (currentMainTab === 'stocks') {
            console.log('실시간 주식 데이터 업데이트 시작');
            
            // 현재 가격 데이터 저장 (하이라이트 비교용)
            const currentPrices = {};
            document.querySelectorAll('.price-cell[data-price]').forEach(cell => {
                const stockCode = cell.closest('tr')?.querySelector('code')?.textContent;
                const price = parseFloat(cell.dataset.price);
                if (stockCode && price) {
                    currentPrices[stockCode] = price;
                }
            });
            
            // 새 데이터 로드
            await stocksManager.loadStocks();
            
            // 가격 변경 하이라이트 적용
            document.querySelectorAll('.price-cell[data-price]').forEach(cell => {
                const stockCode = cell.closest('tr')?.querySelector('code')?.textContent;
                const newPrice = parseFloat(cell.dataset.price);
                const oldPrice = currentPrices[stockCode];
                
                if (stockCode && newPrice && oldPrice && newPrice !== oldPrice) {
                    highlightPriceChange(stockCode, newPrice, oldPrice);
                }
            });
        }
    }, 10000); // 10초 간격
    
    console.log('실시간 업데이트 시작 (10초 간격)');
}

// 종목/기업 추가 모달 열기
function openAddModal(type, stockCode = null) {
    console.log(`${type} ${stockCode ? '수정' : '추가'} 모달 열기`);
    
    if (type === 'stock') {
        elements.addModalTitle.textContent = stockCode ? '종목 수정' : '종목 추가';
        elements.stockFields.style.display = 'block';
        elements.companyFields.style.display = 'none';
        
        // 수정 모드인 경우 데이터 로드
        if (stockCode) {
            loadStockDataForEdit(stockCode);
        }
    } else if (type === 'company') {
        elements.addModalTitle.textContent = '기업 추가';
        elements.stockFields.style.display = 'none';
        elements.companyFields.style.display = 'block';
    }
    
    // 폼 초기화 (수정 모드가 아닌 경우만)
    if (!stockCode) {
        if (type === 'stock') {
            resetAddStockForm();
        } else {
            elements.addForm.reset();
        }
    }
    
    // 모달 표시
    elements.addModal.style.display = 'flex';
    
    // 첫 번째 입력 필드에 포커스
    setTimeout(() => {
        const firstInput = elements.addModal.querySelector('input[type="text"]:not([readonly])');
        if (firstInput) {
            firstInput.focus();
        }
    }, 100);
    
    // 종목코드 실시간 검증 이벤트 추가
    setupStockCodeValidation();
}

// 종목/기업 추가 모달 닫기
function closeAddModal() {
    elements.addModal.style.display = 'none';
    elements.addForm.reset();
    
    // 검증 메시지 초기화
    const validationSpan = document.getElementById('stock-code-validation');
    if (validationSpan) {
        validationSpan.textContent = '';
        validationSpan.className = 'field-validation';
    }
}

// 종목코드 실시간 검증 설정
function setupStockCodeValidation() {
    const stockCodeInput = document.getElementById('stock-code');
    const validationSpan = document.getElementById('stock-code-validation');
    
    if (!stockCodeInput || !validationSpan) return;
    
    stockCodeInput.addEventListener('input', (e) => {
        const value = e.target.value.trim();
        
        if (!value) {
            validationSpan.textContent = '';
            validationSpan.className = 'field-validation';
            return;
        }
        
        // 6자리 숫자 검증
        if (!/^\d{6}$/.test(value)) {
            validationSpan.textContent = '종목코드는 6자리 숫자여야 합니다.';
            validationSpan.className = 'field-validation error';
            return;
        }
        
        // 중복 검사
        const existingStocks = stocksManager.getAllStocks();
        if (existingStocks[value]) {
            validationSpan.textContent = '이미 등록된 종목코드입니다.';
            validationSpan.className = 'field-validation error';
            return;
        }
        
        validationSpan.textContent = '사용 가능한 종목코드입니다.';
        validationSpan.className = 'field-validation success';
    });
}

// 수정을 위한 종목 데이터 로드
async function loadStockDataForEdit(stockCode) {
    try {
        const allStocks = stocksManager.getAllStocks();
        const stockInfo = allStocks[stockCode];
        
        if (!stockInfo) {
            showToast('종목 정보를 찾을 수 없습니다.', 'error');
            return;
        }
        
        // 기본 정보
        document.getElementById('stock-code').value = stockCode;
        document.getElementById('stock-code').readOnly = true; // 수정 시 코드 변경 불가
        document.getElementById('stock-name').value = stockInfo.name || '';
        
        // 카테고리 설정
        const category = stockInfo.category === '메자닌' ? '기타' : '매수'; // 매수/기타로 매핑
        document.querySelector(`input[name="stock-category-radio"][value="${category}"]`).checked = true;
        
        // 가격 정보
        document.getElementById('current-price').value = stockInfo.current_price || '';
        document.getElementById('acquisition-price').value = stockInfo.acquisition_price || '';
        document.getElementById('target-price').value = stockInfo.target_price || '';
        document.getElementById('stop-loss').value = stockInfo.stop_loss || '';
        
        // 알림 설정
        const alertSettings = stockInfo.alert_settings || {};
        document.getElementById('price-alert-enabled').checked = alertSettings.target_stop_enabled !== false;
        document.getElementById('volatility-alert-enabled').checked = alertSettings.volatility_enabled !== false;
        document.getElementById('surge-threshold').value = alertSettings.surge_threshold || 5;
        document.getElementById('drop-threshold').value = alertSettings.drop_threshold || -5;
        
        // 메모
        document.getElementById('stock-memo').value = stockInfo.memo || '';
        
    } catch (error) {
        console.error('종목 데이터 로드 실패:', error);
        showToast('종목 데이터 로드 중 오류가 발생했습니다.', 'error');
    }
}

// 종목/기업 추가 처리
async function handleAddSubmit() {
    try {
        const isStock = elements.stockFields.style.display !== 'none';
        
        if (isStock) {
            await handleAddStock();
        } else {
            await handleAddCompany();
        }
        
        closeAddModal();
        
    } catch (error) {
        console.error('추가 처리 중 오류:', error);
        ui.showToast(`추가 실패: ${error.message}`, 'error');
    }
}

// 종목 추가 처리
async function handleAddStock() {
    // 폼 데이터 수집
    const stockCode = document.getElementById('stock-code').value.trim();
    const stockName = document.getElementById('stock-name').value.trim();
    
    // 라디오 버튼에서 카테고리 가져오기
    const categoryRadio = document.querySelector('input[name="stock-category-radio"]:checked');
    const category = categoryRadio ? categoryRadio.value : '';
    
    // 가격 정보
    const currentPrice = parseInt(document.getElementById('current-price').value) || 0;
    const acquisitionPrice = parseInt(document.getElementById('acquisition-price').value) || 0;
    const targetPrice = parseInt(document.getElementById('target-price').value) || 0;
    const stopLoss = parseInt(document.getElementById('stop-loss').value) || 0;
    
    // 알림 설정
    const priceAlertEnabled = document.getElementById('price-alert-enabled').checked;
    const volatilityAlertEnabled = document.getElementById('volatility-alert-enabled').checked;
    const surgeThreshold = parseFloat(document.getElementById('surge-threshold').value) || 5.0;
    const dropThreshold = parseFloat(document.getElementById('drop-threshold').value) || -5.0;
    
    // 메모
    const memo = document.getElementById('stock-memo').value.trim();
    
    // 기본 유효성 검사
    if (!stockCode || stockCode.length !== 6) {
        throw new Error('종목코드는 6자리여야 합니다.');
    }
    
    if (!stockName) {
        throw new Error('종목명을 입력해주세요.');
    }
    
    if (!category) {
        throw new Error('구분을 선택해주세요.');
    }
    
    // 가격 유효성 검사 (선택사항)
    if (targetPrice > 0 && stopLoss > 0 && stopLoss >= targetPrice) {
        throw new Error('손절가는 목표가보다 낮아야 합니다.');
    }
    
    // 급등급락 임계값 검사
    if (volatilityAlertEnabled) {
        if (surgeThreshold <= 0 || surgeThreshold > 50) {
            throw new Error('급등 임계값은 0%와 50% 사이여야 합니다.');
        }
        
        if (dropThreshold >= 0 || dropThreshold < -50) {
            throw new Error('급락 임계값은 0%와 -50% 사이여야 합니다.');
        }
    }
    
    // API 요청 데이터 준비
    const stockData = {
        stock_code: stockCode,
        stock_name: stockName,
        category: category,
        current_price: currentPrice,
        acquisition_price: acquisitionPrice,
        target_price: targetPrice,
        stop_loss: stopLoss,
        alert_settings: {
            price_alert_enabled: priceAlertEnabled,
            volatility_alert_enabled: volatilityAlertEnabled,
            surge_threshold: surgeThreshold,
            drop_threshold: dropThreshold
        },
        memo: memo
    };
    
    console.log('종목 추가 요청:', stockData);
    
    // API 호출
    const result = await api.addStock(stockData);
    
    if (result && result.success) {
        ui.showToast(result.message || `종목 "${stockName}" 추가가 완료되었습니다.`, 'success');
        
        // 폼 초기화
        resetAddStockForm();
    } else {
        throw new Error(result?.error || '종목 추가에 실패했습니다');
    }
    
    // 주식 데이터 새로고침
    dataLoader.loadStocks();
}

// 종목 추가 폼 초기화
function resetAddStockForm() {
    // 기본 필드 초기화
    document.getElementById('stock-code').value = '';
    document.getElementById('stock-name').value = '';
    document.getElementById('current-price').value = '';
    document.getElementById('acquisition-price').value = '';
    document.getElementById('target-price').value = '';
    document.getElementById('stop-loss').value = '';
    document.getElementById('stock-memo').value = '';
    
    // 라디오 버튼 초기화 (매수를 기본값으로)
    const defaultRadio = document.querySelector('input[name="stock-category-radio"][value="매수"]');
    if (defaultRadio) {
        defaultRadio.checked = true;
    }
    
    // 체크박스 초기화 (활성화가 기본값)
    document.getElementById('price-alert-enabled').checked = true;
    document.getElementById('volatility-alert-enabled').checked = true;
    
    // 임계값 초기화
    document.getElementById('surge-threshold').value = '5';
    document.getElementById('drop-threshold').value = '-5';
    
    // 유효성 검사 메시지 초기화
    const validationSpan = document.getElementById('stock-code-validation');
    if (validationSpan) {
        validationSpan.textContent = '';
        validationSpan.className = 'field-validation';
    }
    
    console.log('종목 추가 폼이 초기화되었습니다.');
}

// 기업 추가 처리  
async function handleAddCompany() {
    const companyCode = document.getElementById('company-code').value.trim();
    const companyName = document.getElementById('company-name').value.trim();
    
    // 유효성 검사
    if (!companyCode) {
        throw new Error('기업코드를 입력해주세요.');
    }
    
    if (!companyName) {
        throw new Error('기업명을 입력해주세요.');
    }
    
    console.log('기업 추가 요청:', { companyCode, companyName });
    
    // API 호출하여 기업 추가
    const result = await api.addCompany({ 
        company_code: companyCode, 
        company_name: companyName 
    });
    
    if (result && result.success) {
        ui.showToast(result.message || `기업 "${companyName}" 추가가 완료되었습니다.`, 'success');
    } else {
        throw new Error(result?.error || '기업 추가에 실패했습니다');
    }
    
    // DART 데이터 새로고침
    if (typeof dartManager !== 'undefined' && dartManager.loadCompanies) {
        dartManager.loadCompanies();
    }
}

// 종목 삭제 처리
async function handleDeleteStock(stockCode, stockName) {
    try {
        const confirmed = confirm(`"${stockName}" 종목을 삭제하시겠습니까?\n\n삭제된 종목은 복구할 수 없습니다.`);
        if (!confirmed) return;
        
        console.log('종목 삭제 요청:', { stockCode, stockName });
        
        // API 호출하여 종목 삭제
        const result = await api.deleteStock(stockCode);
        
        if (result && result.success) {
            ui.showToast(result.message || `종목 "${stockName}" 삭제가 완료되었습니다.`, 'success');
        } else {
            throw new Error(result?.error || '종목 삭제에 실패했습니다');
        }
        
        // 주식 데이터 새로고침
        dataLoader.loadStocks();
        
    } catch (error) {
        console.error('종목 삭제 중 오류:', error);
        ui.showToast(`종목 삭제 실패: ${error.message}`, 'error');
    }
}

// 기업 삭제 처리
async function handleDeleteCompany(companyCode, companyName) {
    try {
        const confirmed = confirm(`"${companyName}" 기업을 삭제하시겠습니까?\n\n삭제된 기업은 복구할 수 없습니다.`);
        if (!confirmed) return;
        
        console.log('기업 삭제 요청:', { companyCode, companyName });
        
        // API 호출하여 기업 삭제
        const result = await api.deleteCompany(companyCode);
        
        if (result && result.success) {
            ui.showToast(result.message || `기업 "${companyName}" 삭제가 완료되었습니다.`, 'success');
        } else {
            throw new Error(result?.error || '기업 삭제에 실패했습니다');
        }
        
        // DART 데이터 새로고침
        if (typeof dartManager !== 'undefined' && dartManager.loadCompanies) {
            dartManager.loadCompanies();
        }
        
    } catch (error) {
        console.error('기업 삭제 중 오류:', error);
        ui.showToast(`기업 삭제 실패: ${error.message}`, 'error');
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', init);

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});