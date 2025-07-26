/**
 * 투자본부 모니터링 시스템 v3 - 프론트엔드 JavaScript
 * Flask 백엔드 API와 연동하여 실시간 데이터 표시
 */

// 전역 변수
let currentStockTab = 'all';
let currentAlertFilter = 'all';
let refreshInterval;

// API 기본 URL
const API_BASE = window.location.origin;

// DOM 요소들
const elements = {
    // 상태 표시
    dartStatus: document.getElementById('dart-status'),
    stockStatus: document.getElementById('stock-status'),
    systemUptime: document.getElementById('system-uptime'),
    
    // 주식 관련
    stocksTable: document.getElementById('stocks-table'),
    stocksTableBody: document.getElementById('stocks-table-body'),
    loadingStocks: document.getElementById('loading-stocks'),
    noStocks: document.getElementById('no-stocks'),
    totalStocks: document.getElementById('total-stocks'),
    lastStockUpdate: document.getElementById('last-stock-update'),
    
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
        const color = value > 0 ? 'red' : value < 0 ? 'blue' : 'black';
        const sign = value > 0 ? '+' : '';
        return `<span style="color: ${color}; font-weight: bold;">${sign}${value.toFixed(2)}%</span>`;
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

// API 호출 함수들
const api = {
    // 시스템 상태 조회
    async getStatus() {
        try {
            const response = await fetch(`${API_BASE}/api/status`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('시스템 상태 조회 실패:', error);
            throw error;
        }
    },
    
    // 주식 목록 조회
    async getStocks() {
        try {
            const response = await fetch(`${API_BASE}/api/stocks`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('주식 목록 조회 실패:', error);
            throw error;
        }
    },
    
    // 주식 수동 업데이트
    async updateStocks() {
        try {
            const response = await fetch(`${API_BASE}/api/stocks/update`, {
                method: 'POST'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
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
            const response = await fetch(`${API_BASE}/api/alerts?${params}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('알림 목록 조회 실패:', error);
            throw error;
        }
    },
    
    // DART 수동 확인
    async checkDart() {
        try {
            const response = await fetch(`${API_BASE}/api/dart/check`, {
                method: 'POST'
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('DART 확인 실패:', error);
            throw error;
        }
    },
    
    // 이메일 테스트
    async testEmail() {
        try {
            const response = await fetch(`${API_BASE}/api/test/email`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    subject: '[테스트] 투자본부 모니터링 시스템 v3',
                    message: '이메일 발송 테스트입니다.'
                })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('이메일 테스트 실패:', error);
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
        
        // 현재 탭에 따른 필터링
        const filteredStocks = stocks.filter(([code, info]) => {
            if (currentStockTab === 'all') return true;
            if (currentStockTab === 'mezzanine') return info.category === '메자닌';
            if (currentStockTab === 'others') return info.category === '주식';
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
            if (currentStockTab === 'mezzanine' || (currentStockTab === 'all' && category === '메자닌')) {
                const conversionPrice = info.conversion_price || info.current_price;
                const parity = conversionPrice && info.current_price ? 
                    ((info.current_price / conversionPrice) * 100).toFixed(1) + '%' : '-';
                extraColumns = `<td>${parity}</td>`;
            }
            
            row.innerHTML = `
                <td><code>${code}</code></td>
                <td><strong>${info.name || code}</strong></td>
                <td><span class="category-badge category-${category === '메자닌' ? 'mezzanine' : 'others'}">${category}</span></td>
                <td class="text-right">${currentPrice}</td>
                <td class="text-right">${changePercent}</td>
                ${extraColumns}
                <td class="text-right">${targetPrice}</td>
                <td class="text-right">${stopLoss}</td>
                <td class="text-center">${lastUpdated}</td>
                <td class="text-center">${status}</td>
            `;
            
            elements.stocksTableBody.appendChild(row);
        });
        
        // 테이블 표시
        elements.loadingStocks.style.display = 'none';
        elements.noStocks.style.display = 'none';
        elements.stocksTable.style.display = 'table';
    },
    
    // 테이블 헤더 업데이트
    updateTableHeaders() {
        const thead = elements.stocksTable.querySelector('thead tr');
        
        if (currentStockTab === 'mezzanine') {
            thead.innerHTML = `
                <th>종목코드</th>
                <th>종목명</th>
                <th>구분</th>
                <th>현재가</th>
                <th>등락률</th>
                <th>패리티(%)</th>
                <th>목표가(TP)</th>
                <th>손절가(SL)</th>
                <th>마지막 업데이트</th>
                <th>상태</th>
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
                <th>마지막 업데이트</th>
                <th>상태</th>
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
            const response = await fetch(`${API_BASE}/api/alerts/${alertId}/read`, {
                method: 'PATCH'
            });
            
            if (response.ok) {
                // 해당 알림 아이템을 읽음으로 표시
                const alertItem = document.querySelector(`[data-id="${alertId}"]`).closest('.alert-item');
                alertItem.classList.remove('unread');
                alertItem.classList.add('read');
                alertItem.querySelector('.btn-mark-read').remove();
                
                this.showToast('알림을 읽음으로 처리했습니다.', 'success');
            }
        } catch (error) {
            console.error('알림 읽음 처리 실패:', error);
            this.showToast('알림 처리에 실패했습니다.', 'error');
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
    }
};

// 데이터 로딩 함수들
const dataLoader = {
    // 시스템 상태 로드
    async loadSystemStatus() {
        try {
            const data = await api.getStatus();
            ui.updateSystemStatus(data);
        } catch (error) {
            console.error('시스템 상태 로드 실패:', error);
        }
    },
    
    // 주식 데이터 로드
    async loadStocks() {
        try {
            elements.loadingStocks.style.display = 'block';
            elements.stocksTable.style.display = 'none';
            elements.noStocks.style.display = 'none';
            
            const data = await api.getStocks();
            ui.updateStockTable(data);
        } catch (error) {
            console.error('주식 데이터 로드 실패:', error);
            ui.showEmptyStocks();
            ui.showToast('주식 데이터 로드에 실패했습니다.', 'error');
        }
    },
    
    // 알림 데이터 로드
    async loadAlerts() {
        try {
            elements.loadingAlerts.style.display = 'block';
            elements.alertsList.style.display = 'none';
            elements.noAlerts.style.display = 'none';
            
            const data = await api.getAlerts(1, currentAlertFilter);
            ui.updateAlertsList(data);
        } catch (error) {
            console.error('알림 데이터 로드 실패:', error);
            ui.showEmptyAlerts();
            ui.showToast('알림 데이터 로드에 실패했습니다.', 'error');
        }
    },
    
    // 모든 데이터 로드
    async loadAllData() {
        await Promise.all([
            this.loadSystemStatus(),
            this.loadStocks(),
            this.loadAlerts()
        ]);
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
            ui.showToast('주식 가격을 업데이트하고 있습니다...', 'info');
            
            const result = await api.updateStocks();
            
            if (result.success) {
                ui.showToast(result.message, 'success');
                await dataLoader.loadStocks();
            } else {
                ui.showToast('주식 업데이트에 실패했습니다.', 'error');
            }
        } catch (error) {
            console.error('주식 수동 업데이트 실패:', error);
            ui.showToast('주식 업데이트 중 오류가 발생했습니다.', 'error');
        }
    },
    
    // DART 수동 확인
    async handleManualDartCheck() {
        try {
            ui.showToast('DART 공시를 확인하고 있습니다...', 'info');
            
            const result = await api.checkDart();
            
            if (result.success) {
                const message = result.disclosures.length > 0 ? 
                    `새로운 공시 ${result.disclosures.length}건을 발견했습니다.` :
                    '새로운 공시가 없습니다.';
                ui.showToast(message, 'success');
                
                if (result.disclosures.length > 0) {
                    await dataLoader.loadAlerts();
                }
            } else {
                ui.showToast('DART 확인에 실패했습니다.', 'error');
            }
        } catch (error) {
            console.error('DART 수동 확인 실패:', error);
            ui.showToast('DART 확인 중 오류가 발생했습니다.', 'error');
        }
    },
    
    // 이메일 테스트
    async handleEmailTest() {
        try {
            ui.showToast('테스트 이메일을 발송하고 있습니다...', 'info');
            
            const result = await api.testEmail();
            
            if (result.success) {
                ui.showToast('테스트 이메일이 발송되었습니다.', 'success');
            } else {
                ui.showToast('이메일 발송에 실패했습니다.', 'error');
            }
        } catch (error) {
            console.error('이메일 테스트 실패:', error);
            ui.showToast('이메일 테스트 중 오류가 발생했습니다.', 'error');
        }
    }
};

// 초기화 함수
function init() {
    console.log('투자본부 모니터링 시스템 v3 초기화');
    
    // 초기 데이터 로드
    dataLoader.loadAllData();
    
    // 탭 버튼 이벤트 연결
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            eventHandlers.handleStockTabChange(tab);
        });
    });
    
    // 알림 필터 버튼 이벤트 연결
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const filter = e.target.dataset.filter;
            eventHandlers.handleAlertFilterChange(filter);
        });
    });
    
    // 새로고침 버튼들
    document.getElementById('refresh-stocks')?.addEventListener('click', () => {
        dataLoader.loadStocks();
    });
    
    document.getElementById('refresh-alerts')?.addEventListener('click', () => {
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
    
    // 자동 새로고침 설정 (30초마다)
    refreshInterval = setInterval(() => {
        dataLoader.loadSystemStatus();
        dataLoader.loadStocks();
        dataLoader.loadAlerts();
    }, 30000);
    
    console.log('초기화 완료');
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', init);

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});