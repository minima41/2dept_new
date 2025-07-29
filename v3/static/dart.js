/**
 * DART 공시 관리 페이지 - JavaScript
 * Flask 백엔드 API와 연동하여 DART 모니터링 시스템 관리
 */

// 메타마스크 충돌 방지
if (typeof window.ethereum !== 'undefined') {
    console.warn('MetaMask detected - potential conflicts may occur');
}

// 전역 변수
let refreshInterval;
let elements; // DOM 요소들은 초기화 시점에 정의

// DOM 요소 선택자 매핑
const ELEMENT_SELECTORS = {
    // 상태 표시 요소들
    dartStatus: 'dart-status',
    lastCheckTime: 'last-check-time',
    
    // 데이터 표시 컨테이너들
    companiesList: 'companies-list',
    companiesCount: 'companies-count',
    keywordsList: 'keywords-list',
    keywordsCount: 'keywords-count',
    sectionsList: 'sections-list',
    disclosuresList: 'disclosures-list',
    disclosuresToday: 'disclosures-today',
    processedCount: 'processed-count',
    monitoredStocksList: 'monitored-stocks-list',
    
    // 컨트롤 버튼들
    refreshCompanies: 'refresh-companies',
    refreshKeywords: 'refresh-keywords',
    refreshDisclosures: 'refresh-disclosures',
    refreshMonitoredStocks: 'refresh-monitored-stocks',
    refreshLogs: 'refresh-logs',
    refreshAll: 'refresh-all',
    manualCheck: 'manual-check',
    addCompany: 'add-company',
    addKeyword: 'add-keyword',
    
    // 필터 및 입력 요소들
    companyFilter: 'company-filter',
    dateFilter: 'date-filter',
    logHours: 'log-hours',
    
    // 로그 표시 영역
    dartLogs: 'dart-logs'
};

// DOM 요소 초기화 함수
function initializeElements() {
    console.log('DOM 요소 초기화 시작...');
    
    const elements = {};
    const missingElements = [];
    
    // 모든 요소 ID를 확인하고 DOM 요소 참조 생성
    for (const [key, id] of Object.entries(ELEMENT_SELECTORS)) {
        const element = document.getElementById(id);
        if (element) {
            elements[key] = element;
            console.log(`✅ DOM 요소 로드 성공: ${key} (${id})`);
        } else {
            missingElements.push(`${key} (${id})`);
            console.warn(`⚠️ DOM 요소 누락: ${key} (${id})`);
        }
    }
    
    // 누락된 요소가 있어도 초기화된 요소들은 반환
    if (missingElements.length > 0) {
        console.warn('일부 DOM 요소가 누락되었습니다:', missingElements);
        console.warn('누락된 요소들은 해당 기능이 비활성화될 수 있습니다.');
    }
    
    console.log(`DOM 요소 초기화 완료: ${Object.keys(elements).length}개 요소 로드됨`);
    return elements;
}

// 공통 에러 처리 함수들
const errorHandler = {
    // API 에러 처리 및 사용자 친화적 메시지 표시
    handleError(error, context = '') {
        console.error(`API 에러 ${context}:`, error);
        
        let userMessage = '알 수 없는 오류가 발생했습니다.';
        
        if (error.message) {
            if (error.message.includes('404')) {
                userMessage = '요청한 데이터를 찾을 수 없습니다.';
            } else if (error.message.includes('500')) {
                userMessage = '서버 내부 오류가 발생했습니다.';
            } else if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
                userMessage = '네트워크 연결을 확인해주세요.';
            } else {
                userMessage = error.message;
            }
        }
        
        // 에러 로깅
        console.group(`🚨 DART 페이지 에러 ${context}`);
        console.error('사용자 메시지:', userMessage);
        console.error('원본 에러:', error);
        console.groupEnd();
        
        return userMessage;
    },
    
    // 표준 에러 표시
    showError(error, context = '') {
        const userMessage = this.handleError(error, context);
        utils.showAlert(userMessage, 'error');
        return userMessage;
    }
};

// API 호출 함수들
const api = {
    async getStatus() {
        const response = await fetch(`${window.API_BASE}/api/v1/status`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async getCompanies() {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/companies`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async getKeywords() {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/keywords`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async getDisclosures(filters = {}) {
        const params = new URLSearchParams();
        if (filters.date) params.append('date', filters.date);
        if (filters.company) params.append('company', filters.company);
        if (filters.limit) params.append('limit', filters.limit);
        
        const response = await fetch(`${window.API_BASE}/api/v1/dart/disclosures?${params}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async manualCheck() {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async getProcessedIds() {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/processed-ids`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async getMonitoredStocks() {
        const response = await fetch(`${window.API_BASE}/api/v1/stocks`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async addCompany(companyCode, companyName) {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/companies`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                company_code: companyCode,
                company_name: companyName
            })
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async deleteCompany(companyCode) {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/companies/${companyCode}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async addKeyword(keyword) {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/keywords/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                keyword: keyword
            })
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async deleteKeyword(keyword) {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/keywords/${encodeURIComponent(keyword)}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    },
    
    async getDartLogs(hours = 24) {
        const response = await fetch(`${window.API_BASE}/api/v1/dart/realtime-logs?hours=${hours}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    }
};

// 유틸리티 함수들
const utils = {
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR') + ' ' + date.toLocaleTimeString('ko-KR');
    },
    
    formatDateYMD(dateString) {
        if (!dateString) return '';
        // YYYYMMDD 형식을 YYYY-MM-DD로 변환
        if (dateString.length === 8) {
            return `${dateString.substr(0,4)}-${dateString.substr(4,2)}-${dateString.substr(6,2)}`;
        }
        return dateString;
    },
    
    getDefaultDateRange() {
        const today = new Date();
        const oneWeekAgo = new Date(today);
        oneWeekAgo.setDate(today.getDate() - 7);
        
        return {
            startDate: oneWeekAgo.toISOString().split('T')[0],
            endDate: today.toISOString().split('T')[0]
        };
    },
    
    // 날짜 형식 검증 (YYYY-MM-DD)
    validateDateInput(dateString) {
        if (!dateString) return false;
        
        // YYYY-MM-DD 형식 확인
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        if (!dateRegex.test(dateString)) {
            return false;
        }
        
        // 실제 유효한 날짜인지 확인
        const date = new Date(dateString);
        const [year, month, day] = dateString.split('-').map(Number);
        
        return date.getFullYear() === year &&
               date.getMonth() === month - 1 &&
               date.getDate() === day;
    },
    
    // 날짜 입력 검증 및 에러 표시
    validateAndShowDateError(dateString, fieldName = '날짜') {
        if (!dateString) {
            this.showAlert(`${fieldName}를 입력해주세요.`, 'warning');
            return false;
        }
        
        if (!this.validateDateInput(dateString)) {
            this.showAlert(`올바른 ${fieldName} 형식이 아닙니다. (YYYY-MM-DD)`, 'error');
            return false;
        }
        
        // 너무 과거나 미래 날짜 체크
        const inputDate = new Date(dateString);
        const today = new Date();
        const oneYearAgo = new Date(today);
        oneYearAgo.setFullYear(today.getFullYear() - 2);
        
        if (inputDate > today) {
            this.showAlert('미래 날짜는 입력할 수 없습니다.', 'warning');
            return false;
        }
        
        if (inputDate < oneYearAgo) {
            this.showAlert('2년 이전 날짜는 조회할 수 없습니다.', 'warning');
            return false;
        }
        
        return true;
    },
    
    showAlert(message, type = 'info') {
        // 향상된 Toast 알림 시스템
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // 기존 toast 제거
        const existingToasts = document.querySelectorAll('.dart-toast');
        existingToasts.forEach(toast => toast.remove());
        
        // Toast 컨테이너 생성
        const toast = document.createElement('div');
        toast.className = `dart-toast dart-toast-${type}`;
        
        // 타입별 아이콘
        const icons = {
            'info': 'fas fa-info-circle',
            'success': 'fas fa-check-circle', 
            'warning': 'fas fa-exclamation-triangle',
            'error': 'fas fa-times-circle'
        };
        
        toast.innerHTML = `
            <div class="toast-content">
                <i class="${icons[type] || icons.info}"></i>
                <span class="toast-message">${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Toast 스타일 설정
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: '10000',
            minWidth: '300px',
            maxWidth: '500px',
            padding: '1rem',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            fontSize: '0.875rem',
            fontFamily: 'inherit',
            opacity: '0',
            transform: 'translateX(100%)',
            transition: 'all 0.3s ease-in-out'
        });
        
        // 타입별 색상
        const colors = {
            'info': { bg: '#e3f2fd', border: '#2196f3', text: '#1565c0' },
            'success': { bg: '#e8f5e8', border: '#4caf50', text: '#2e7d32' },
            'warning': { bg: '#fff3e0', border: '#ff9800', text: '#ef6c00' },
            'error': { bg: '#ffebee', border: '#f44336', text: '#c62828' }
        };
        
        const color = colors[type] || colors.info;
        Object.assign(toast.style, {
            backgroundColor: color.bg,
            border: `1px solid ${color.border}`,
            color: color.text
        });
        
        // DOM에 추가
        document.body.appendChild(toast);
        
        // 애니메이션 시작
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        });
        
        // 자동 제거 (에러는 더 오래 표시)
        const duration = type === 'error' ? 6000 : 4000;
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 300);
            }
        }, duration);
        
        // 터치/마우스 이벤트로 수동 닫기
        toast.addEventListener('click', (e) => {
            if (e.target.closest('.toast-close')) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 200);
            }
        });
    },
    
    showLoading(show = true, message = '로딩 중...') {
        // 버튼 비활성화로 중복 요청 방지
        const buttons = document.querySelectorAll('button');
        buttons.forEach(btn => {
            if (show) {
                btn.disabled = true;
                btn.style.opacity = '0.6';
            } else {
                btn.disabled = false;
                btn.style.opacity = '1';
            }
        });
        
        if (show) {
            // 로딩 오버레이 생성
            let loadingOverlay = document.getElementById('dart-loading-overlay');
            
            if (!loadingOverlay) {
                loadingOverlay = document.createElement('div');
                loadingOverlay.id = 'dart-loading-overlay';
                
                // 로딩 스타일 설정
                Object.assign(loadingOverlay.style, {
                    position: 'fixed',
                    top: '0',
                    left: '0',
                    width: '100%',
                    height: '100%',
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    zIndex: '9999',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    backdropFilter: 'blur(2px)',
                    opacity: '0',
                    transition: 'opacity 0.2s ease-in-out'
                });
                
                // 로딩 컨텐츠
                loadingOverlay.innerHTML = `
                    <div class="loading-spinner">
                        <div class="spinner-ring"></div>
                    </div>
                    <div class="loading-text">${message}</div>
                `;
                
                // 스타일 추가
                const style = document.createElement('style');
                style.textContent = `
                    .loading-spinner {
                        position: relative;
                        width: 50px;
                        height: 50px;
                        margin-bottom: 1rem;
                    }
                    
                    .spinner-ring {
                        width: 50px;
                        height: 50px;
                        border: 4px solid #f3f4f6;
                        border-top: 4px solid #2196f3;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                    }
                    
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                    
                    .loading-text {
                        font-size: 1rem;
                        color: #666;
                        font-weight: 500;
                        text-align: center;
                    }
                `;
                
                document.head.appendChild(style);
                document.body.appendChild(loadingOverlay);
                
                // 애니메이션 시작
                requestAnimationFrame(() => {
                    loadingOverlay.style.opacity = '1';
                });
            } else {
                // 기존 로딩 메시지 업데이트
                const loadingText = loadingOverlay.querySelector('.loading-text');
                if (loadingText) {
                    loadingText.textContent = message;
                }
                loadingOverlay.style.opacity = '1';
            }
        } else {
            // 로딩 오버레이 제거
            const loadingOverlay = document.getElementById('dart-loading-overlay');
            if (loadingOverlay) {
                loadingOverlay.style.opacity = '0';
                setTimeout(() => {
                    if (loadingOverlay.parentNode) {
                        loadingOverlay.remove();
                    }
                }, 200);
            }
        }
        
        // 기존 로딩 인디케이터도 유지 (호환성)
        const loadingElements = document.querySelectorAll('.loading-indicator');
        loadingElements.forEach(el => {
            el.style.display = show ? 'block' : 'none';
        });
    },
    
    showError(container, message) {
        if (container) {
            container.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                </div>
            `;
        }
    }
};

// 시스템 상태 업데이트
async function updateSystemStatus() {
    try {
        const status = await api.getStatus();
        
        if (status.dart_monitoring) {
            const isEnabled = status.dart_monitoring.enabled;
            const lastCheck = status.dart_monitoring.last_check;
            
            elements.dartStatus.className = `status-indicator ${isEnabled ? 'active' : 'inactive'}`;
            elements.dartStatus.innerHTML = `
                <i class="fas fa-circle"></i> 
                ${isEnabled ? '정상' : '중지'}
            `;
            
            if (lastCheck) {
                elements.lastCheckTime.textContent = utils.formatDate(lastCheck);
            }
        }
        
    } catch (error) {
        console.error('시스템 상태 업데이트 오류:', error);
        elements.dartStatus.className = 'status-indicator error';
        elements.dartStatus.innerHTML = '<i class="fas fa-circle"></i> 오류';
    }
}

// 관심 기업 목록 렌더링
function renderCompanies(companies) {
    if (!companies || companies.length === 0) {
        elements.companiesList.innerHTML = '<p>관심 기업이 없습니다.</p>';
        return;
    }
    
    const companiesHtml = companies.map(company => `
        <div class="item">
            <div class="item-info">
                <div class="item-code">${company.code}</div>
                <div class="item-name">${company.name}</div>
            </div>
            <button class="remove-btn" onclick="deleteCompanyHandler('${company.code}', '${company.name}')" title="삭제">
                ×
            </button>
        </div>
    `).join('');
    
    elements.companiesList.innerHTML = companiesHtml;
    elements.companiesCount.textContent = companies.length;
}

// 키워드 목록 렌더링
function renderKeywords(data) {
    if (!data) return;
    
    // 주요 키워드
    if (data.keywords && data.keywords.length > 0) {
        const keywordsHtml = data.keywords.map(keyword => 
            `<div class="item">
                <div class="item-info">
                    <div class="item-keyword">${keyword}</div>
                </div>
                <button class="remove-btn" onclick="deleteKeywordHandler('${keyword}', 'keyword')" title="삭제">
                    ×
                </button>
            </div>`
        ).join('');
        elements.keywordsList.innerHTML = keywordsHtml;
    } else {
        elements.keywordsList.innerHTML = '<p>등록된 키워드가 없습니다.</p>';
    }
    
    // 중요 섹션
    if (data.important_sections && data.important_sections.length > 0) {
        const sectionsHtml = data.important_sections.map(section => 
            `<span class="keyword-chip">
                ${section}
                <button class="delete-btn" onclick="deleteKeywordHandler('${section}', 'section')" style="margin-left: 0.5rem;">
                    <i class="fas fa-times"></i>
                </button>
            </span>`
        ).join('');
        elements.sectionsList.innerHTML = sectionsHtml;
    } else {
        elements.sectionsList.innerHTML = '<p>등록된 중요 섹션이 없습니다.</p>';
    }
    
    elements.keywordsCount.textContent = data.keyword_count || 0;
}

// 모니터링 종목 목록 렌더링
function renderMonitoredStocks(stocksData) {
    if (!stocksData || !stocksData.stocks || Object.keys(stocksData.stocks).length === 0) {
        elements.monitoredStocksList.innerHTML = '<p>모니터링 중인 종목이 없습니다.</p>';
        return;
    }
    
    const stocks = stocksData.stocks;
    const stocksHtml = Object.entries(stocks).map(([code, stock]) => {
        const changePercent = stock.change_percent || 0;
        const priceClass = changePercent > 0 ? 'price-positive' : 
                          changePercent < 0 ? 'price-negative' : 'price-neutral';
        const changeSign = changePercent > 0 ? '+' : '';
        
        return `
            <div class="stock-card">
                <div class="stock-header">
                    <div>
                        <div class="stock-name">${stock.name}</div>
                        <div class="stock-code">${code}</div>
                    </div>
                    <div class="status-indicator ${stock.enabled ? 'active' : 'inactive'}">
                        <i class="fas fa-circle"></i>
                    </div>
                </div>
                <div style="margin-bottom: 0.5rem;">
                    <div class="stock-price ${priceClass}">
                        ${(stock.current_price || 0).toLocaleString()}원
                    </div>
                    <div style="color: ${priceClass === 'price-positive' ? '#d32f2f' : priceClass === 'price-negative' ? '#1976d2' : '#757575'}; font-size: 0.875rem;">
                        ${changeSign}${changePercent.toFixed(2)}%
                    </div>
                </div>
                <div style="font-size: 0.875rem; color: #666;">
                    <div>목표가: ${(stock.target_price || 0).toLocaleString()}원</div>
                    <div>손절가: ${(stock.stop_loss || 0).toLocaleString()}원</div>
                    <div>카테고리: ${stock.category || '주식'}</div>
                </div>
            </div>
        `;
    }).join('');
    
    elements.monitoredStocksList.innerHTML = stocksHtml;
}

// 공시 목록 렌더링
function renderDisclosures(disclosures) {
    if (!disclosures || disclosures.length === 0) {
        elements.disclosuresList.innerHTML = '<p>공시가 없습니다.</p>';
        elements.disclosuresToday.textContent = '0';
        return;
    }
    
    const disclosuresHtml = disclosures.map(disclosure => {
        const receiptDate = utils.formatDateYMD(disclosure.rcept_dt);
        const dartUrl = `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${disclosure.rcept_no}`;
        
        return `
            <div class="disclosure-item">
                <div class="disclosure-meta">
                    <span><i class="fas fa-building"></i> ${disclosure.corp_name}</span>
                    <span><i class="fas fa-calendar"></i> ${receiptDate}</span>
                    <span><i class="fas fa-hashtag"></i> ${disclosure.rcept_no}</span>
                </div>
                <div class="disclosure-title">
                    <a href="${dartUrl}" target="_blank" class="disclosure-link">
                        ${disclosure.report_nm}
                        <i class="fas fa-external-link-alt" style="margin-left: 0.5rem;"></i>
                    </a>
                </div>
            </div>
        `;
    }).join('');
    
    elements.disclosuresList.innerHTML = disclosuresHtml;
    elements.disclosuresToday.textContent = disclosures.length;
}

// 기업 필터 옵션 업데이트
function updateCompanyFilter(companies) {
    if (!companies) return;
    
    const optionsHtml = companies.map(company => 
        `<option value="${company.code}">${company.name}</option>`
    ).join('');
    
    elements.companyFilter.innerHTML = '<option value="">전체 기업</option>' + optionsHtml;
}

// 데이터 로드 함수들
async function loadCompanies() {
    try {
        utils.showLoading(true, '관심 기업 목록 로드 중...');
        const result = await api.getCompanies();
        
        if (result && result.success) {
            renderCompanies(result.companies);
            updateCompanyFilter(result.companies);
            console.log(`기업 목록 로드 완료: ${result.companies?.length}개`);
        } else {
            const errorMsg = result?.error || '알 수 없는 오류';
            console.error('기업 목록 로드 실패:', errorMsg);
            utils.showError(elements.companiesList, `기업 목록 로드 실패: ${errorMsg}`);
            errorHandler.showError(new Error(errorMsg), '기업 목록 로드');
        }
    } catch (error) {
        console.error('기업 목록 로드 오류:', error);
        utils.showError(elements.companiesList, '기업 목록을 불러올 수 없습니다.');
        errorHandler.showError(error, '기업 목록 로드');
    } finally {
        utils.showLoading(false);
    }
}

async function loadKeywords() {
    try {
        utils.showLoading(true, '키워드 목록 로드 중...');
        const result = await api.getKeywords();
        
        if (result && result.success) {
            renderKeywords(result);
            console.log(`키워드 목록 로드 완료: ${result.keyword_count}개`);
        } else {
            const errorMsg = result?.error || '알 수 없는 오류';
            console.error('키워드 목록 로드 실패:', errorMsg);
            utils.showError(elements.keywordsList, `키워드 목록 로드 실패: ${errorMsg}`);
            utils.showAlert('키워드 목록 로드 실패: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('키워드 목록 로드 오류:', error);
        utils.showError(elements.keywordsList, '키워드 목록을 불러올 수 없습니다.');
        utils.showAlert('키워드 목록 로드 중 네트워크 오류가 발생했습니다.', 'error');
    } finally {
        utils.showLoading(false);
    }
}

async function loadDisclosures() {
    try {
        utils.showLoading(true, '공시 목록 조회 중...');
        
        const filters = {
            limit: 50
        };
        
        if (elements.companyFilter.value) {
            filters.company = elements.companyFilter.value;
        }
        
        if (elements.dateFilter.value) {
            // 날짜 검증
            if (!utils.validateAndShowDateError(elements.dateFilter.value, '조회 날짜')) {
                return; // 검증 실패 시 조회하지 않음
            }
            
            // YYYY-MM-DD를 YYYYMMDD로 변환
            filters.date = elements.dateFilter.value.replace(/-/g, '');
        }
        
        console.log('공시 조회 필터:', filters);
        
        const result = await api.getDisclosures(filters);
        
        if (result && result.success) {
            renderDisclosures(result.disclosures);
            
            // 기본 날짜 사용 여부 표시
            if (result.is_default_date) {
                console.log(`공시 목록 로드 완료 (기본 날짜 사용: ${result.date_used}): ${result.disclosures?.length}개 (총 ${result.total}개)`);
            } else {
                console.log(`공시 목록 로드 완료 (지정 날짜: ${result.date_used}): ${result.disclosures?.length}개 (총 ${result.total}개)`);
            }
        } else {
            const errorMsg = result?.error || '알 수 없는 오류';
            console.error('공시 목록 로드 실패:', errorMsg);
            utils.showError(elements.disclosuresList, `공시 목록 로드 실패: ${errorMsg}`);
            renderDisclosures([]);
            
            // 날짜 형식 오류인 경우 사용자에게 알림
            if (result?.error_code === 'INVALID_DATE_FORMAT') {
                errorHandler.showError(new Error(errorMsg), '날짜 형식 검증');
            }
        }
    } catch (error) {
        console.error('공시 목록 로드 오류:', error);
        utils.showError(elements.disclosuresList, '공시 목록을 불러올 수 없습니다.');
        renderDisclosures([]);
        errorHandler.showError(error, '공시 목록 로드');
    } finally {
        utils.showLoading(false);
    }
}

async function loadProcessedIds() {
    try {
        const result = await api.getProcessedIds();
        
        if (result.success) {
            elements.processedCount.textContent = result.count;
        }
    } catch (error) {
        console.error('처리된 ID 조회 오류:', error);
    }
}

// 모니터링 종목 로드
async function loadMonitoredStocks() {
    try {
        utils.showLoading(true, '모니터링 종목 로드 중...');
        const result = await api.getMonitoredStocks();
        
        if (result && result.success) {
            renderMonitoredStocks(result);
            console.log(`모니터링 종목 로드 완료: ${result.count}개`);
        } else {
            const errorMsg = result?.error || '알 수 없는 오류';
            console.error('모니터링 종목 로드 실패:', errorMsg);
            utils.showError(elements.monitoredStocksList, `모니터링 종목 로드 실패: ${errorMsg}`);
        }
    } catch (error) {
        console.error('모니터링 종목 로드 오류:', error);
        utils.showError(elements.monitoredStocksList, '모니터링 종목을 불러올 수 없습니다.');
    } finally {
        utils.showLoading(false);
    }
}

// 기업 추가 핸들러
async function addCompanyHandler() {
    const companyCode = prompt('기업 코드를 입력해주세요 (예: 005930):');
    if (!companyCode) return;
    
    const companyName = prompt('기업명을 입력해주세요 (예: 삼성전자):');
    if (!companyName) return;
    
    try {
        utils.showLoading(true);
        const result = await api.addCompany(companyCode.trim(), companyName.trim());
        
        if (result && result.success) {
            utils.showAlert(`${companyName} 기업이 추가되었습니다.`);
            await loadCompanies();
        } else {
            utils.showAlert('기업 추가 실패: ' + (result?.error || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('기업 추가 오류:', error);
        utils.showAlert('기업 추가 중 오류가 발생했습니다.');
    } finally {
        utils.showLoading(false);
    }
}

// 기업 삭제 핸들러
async function deleteCompanyHandler(companyCode, companyName) {
    if (!confirm(`정말로 "${companyName}" 기업을 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        utils.showLoading(true);
        const result = await api.deleteCompany(companyCode);
        
        if (result && result.success) {
            utils.showAlert(`${companyName} 기업이 삭제되었습니다.`);
            await loadCompanies();
        } else {
            utils.showAlert('기업 삭제 실패: ' + (result?.error || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('기업 삭제 오류:', error);
        utils.showAlert('기업 삭제 중 오류가 발생했습니다.');
    } finally {
        utils.showLoading(false);
    }
}

// 키워드 추가 핸들러
async function addKeywordHandler() {
    const keyword = prompt('추가할 키워드를 입력해주세요:');
    if (!keyword || !keyword.trim()) return;
    
    try {
        utils.showLoading(true);
        
        // 키워드 추가 API 호출 (백엔드 구현 필요)
        const result = await api.addKeyword(keyword.trim());
        
        if (result && result.success) {
            utils.showAlert(`키워드 "${keyword.trim()}"이 추가되었습니다.`);
            await loadKeywords();
        } else {
            utils.showAlert('키워드 추가 실패: ' + (result?.error || '백엔드 API 구현 필요'));
        }
    } catch (error) {
        console.error('키워드 추가 오류:', error);
        utils.showAlert('키워드 추가 기능은 추후 구현 예정입니다.');
    } finally {
        utils.showLoading(false);
    }
}

// 키워드 삭제 핸들러
async function deleteKeywordHandler(keyword, type) {
    if (!confirm(`정말로 "${keyword}" ${type === 'keyword' ? '키워드' : '중요 섹션'}을 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        utils.showLoading(true);
        const result = await api.deleteKeyword(keyword);
        
        if (result && result.success) {
            utils.showAlert(`"${keyword}"이 삭제되었습니다.`);
            await loadKeywords();
        } else {
            utils.showAlert('키워드 삭제 실패: ' + (result?.error || '백엔드 API 구현 필요'));
        }
    } catch (error) {
        console.error('키워드 삭제 오류:', error);
        utils.showAlert('키워드 삭제 기능은 추후 구현 예정입니다.');
    } finally {
        utils.showLoading(false);
    }
}

// 수동 공시 확인
async function performManualCheck() {
    try {
        utils.showLoading(true, '수동 공시 확인 중...');
        elements.manualCheck.disabled = true;
        elements.manualCheck.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 확인중...';
        
        const result = await api.manualCheck();
        
        if (result.success) {
            utils.showAlert(`수동 확인 완료: ${result.new_disclosures}개의 새로운 공시를 발견했습니다.`);
            
            // 데이터 새로고침
            await loadDisclosures();
            await loadProcessedIds();
            await updateSystemStatus();
        } else {
            utils.showAlert('수동 확인 실패: ' + result.error);
        }
    } catch (error) {
        console.error('수동 확인 오류:', error);
        utils.showAlert('수동 확인 중 오류가 발생했습니다.');
    } finally {
        utils.showLoading(false);
        elements.manualCheck.disabled = false;
        elements.manualCheck.innerHTML = '<i class="fas fa-search"></i> 수동 확인';
    }
}

// 이벤트 리스너 설정
function setupEventListeners() {
    console.log('=== DART 페이지 이벤트 리스너 설정 시작 ===');
    
    // DOM 요소 존재 여부 확인
    const requiredElements = {
        refreshCompanies: elements.refreshCompanies,
        refreshKeywords: elements.refreshKeywords,
        refreshDisclosures: elements.refreshDisclosures,
        refreshMonitoredStocks: elements.refreshMonitoredStocks,
        companyFilter: elements.companyFilter,
        dateFilter: elements.dateFilter,
        manualCheck: elements.manualCheck,
        addCompany: elements.addCompany,
        addKeyword: elements.addKeyword
    };
    
    // 누락된 요소 확인
    const missingElements = [];
    Object.keys(requiredElements).forEach(key => {
        if (!requiredElements[key]) {
            missingElements.push(key);
            console.error(`❌ 누락된 DOM 요소: ${key}`);
        } else {
            console.log(`✅ DOM 요소 확인: ${key}`);
        }
    });
    
    if (missingElements.length > 0) {
        console.error('❌ DOM 요소 누락으로 인한 이벤트 리스너 설정 실패:', missingElements);
        return false;
    }
    // 새로고침 버튼들
    elements.refreshCompanies.addEventListener('click', loadCompanies);
    elements.refreshKeywords.addEventListener('click', loadKeywords);
    elements.refreshDisclosures.addEventListener('click', loadDisclosures);
    elements.refreshMonitoredStocks.addEventListener('click', loadMonitoredStocks);
    
    // 수동 확인 버튼
    elements.manualCheck.addEventListener('click', performManualCheck);
    
    // 추가 버튼들
    elements.addCompany.addEventListener('click', addCompanyHandler);
    elements.addKeyword.addEventListener('click', addKeywordHandler);
    
    // 새로운 UI 요소들
    if (elements.refreshLogs) {
        elements.refreshLogs.addEventListener('click', loadDartLogs);
    }
    if (elements.refreshAll) {
        elements.refreshAll.addEventListener('click', refreshAll);
    }
    if (elements.logHours) {
        elements.logHours.addEventListener('change', loadDartLogs);
    }
    
    // 필터 변경
    elements.companyFilter.addEventListener('change', loadDisclosures);
    
    // 날짜 필터 변경 시 검증 후 조회
    elements.dateFilter.addEventListener('change', (event) => {
        const dateValue = event.target.value;
        
        // 빈 값이면 바로 조회 (기본값 사용)
        if (!dateValue) {
            loadDisclosures();
            return;
        }
        
        // 날짜 검증
        if (utils.validateAndShowDateError(dateValue, '조회 날짜')) {
            loadDisclosures();
        } else {
            // 검증 실패 시 이전 값으로 복원하거나 기본값으로 설정
            console.warn('잘못된 날짜 입력, 기본값으로 복원');
            event.target.value = new Date().toISOString().split('T')[0];
        }
    });
    
    // 날짜 입력 시 실시간 검증 (입력 완료 후)
    elements.dateFilter.addEventListener('blur', (event) => {
        const dateValue = event.target.value;
        if (dateValue && !utils.validateDateInput(dateValue)) {
            utils.showAlert('올바른 날짜 형식이 아닙니다. (YYYY-MM-DD)', 'warning');
            // 포커스를 다시 날짜 필드로 이동
            setTimeout(() => event.target.focus(), 100);
        }
        });
        
        console.log('✅ DART 페이지 이벤트 리스너 설정 완료!');
        return true;
        }

// 초기화 함수
async function initialize() {
    console.log('DART 관리 페이지 초기화 시작');
    
    try {
        // 1. DOM 요소 초기화 (최우선)
        elements = initializeElements();
        
        // 2. DOM 요소 초기화 검증
        if (!elements || Object.keys(elements).length === 0) {
            console.error('필수 DOM 요소 초기화 실패');
            utils.showAlert('페이지 초기화 중 오류가 발생했습니다. 페이지를 새로고침해 주세요.', 'error');
            return;
        }
        
        // 3. 이벤트 리스너 설정
        const eventListenerResult = setupEventListeners();
        if (!eventListenerResult) {
            console.error('이벤트 리스너 설정 실패');
            return;
        }
        
        // 날짜 필터 기본값 설정 (오늘 날짜를 기본으로)
        if (elements.dateFilter) {
            const today = new Date();
            const todayString = today.toISOString().split('T')[0]; // YYYY-MM-DD 형식
            elements.dateFilter.value = todayString;
            
            // 날짜 필터에 최대값 설정 (오늘까지만 선택 가능)
            elements.dateFilter.max = todayString;
            
            // 최소값 설정 (2년 전까지만 선택 가능)
            const twoYearsAgo = new Date(today);
            twoYearsAgo.setFullYear(today.getFullYear() - 2);
            elements.dateFilter.min = twoYearsAgo.toISOString().split('T')[0];
            
            console.log(`날짜 필터 기본값 설정: ${todayString} (범위: ${elements.dateFilter.min} ~ ${elements.dateFilter.max})`);
        }
        
        // 초기 데이터 로드
        console.log('초기 데이터 로드 시작...');
        
        // 병렬로 로드하되 실패해도 다른 데이터는 계속 로드
        const loadPromises = [
            updateSystemStatus().catch(err => console.error('시스템 상태 로드 실패:', err)),
            loadCompanies().catch(err => console.error('기업 목록 로드 실패:', err)),
            loadKeywords().catch(err => console.error('키워드 로드 실패:', err)),
            loadProcessedIds().catch(err => console.error('처리된 ID 로드 실패:', err)),
            loadMonitoredStocks().catch(err => console.error('모니터링 종목 로드 실패:', err)),
            loadDartLogs().catch(err => console.error('DART 로그 로드 실패:', err))
        ];
        
        // 기본 데이터 로드 후 공시 목록 로드
        await Promise.allSettled(loadPromises);
        
        // 공시 목록은 다른 데이터가 로드된 후에 실행
        await loadDisclosures().catch(err => console.error('공시 목록 로드 실패:', err));
        
        // 주기적 업데이트 설정 (30초마다)
        refreshInterval = setInterval(async () => {
            try {
                await updateSystemStatus();
                await loadDartLogs(); // 로그도 주기적으로 갱신
            } catch (error) {
                console.error('주기적 상태 업데이트 실패:', error);
            }
        }, 30000);
        
        console.log('DART 관리 페이지 초기화 완료');
        
    } catch (error) {
        console.error('DART 페이지 초기화 중 오류:', error);
        utils.showAlert('페이지 초기화 중 오류가 발생했습니다. 페이지를 새로고침해 주세요.', 'error');
    }
}

// 페이지 언로드 시 인터벌 정리
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// 실시간 로그 로드
async function loadDartLogs() {
    try {
        const hours = parseInt(elements.logHours?.value || '24');
        const result = await api.getDartLogs(hours);
        
        if (result && result.success) {
            renderDartLogs(result.logs);
            console.log(`DART 로그 로드 완료: ${result.total_count}건`);
        } else {
            const errorMsg = result?.error || '알 수 없는 오류';
            console.error('DART 로그 로드 실패:', errorMsg);
            if (elements.dartLogs) {
                elements.dartLogs.innerHTML = '<div class="log-entry error">로그를 불러올 수 없습니다.</div>';
            }
        }
    } catch (error) {
        console.error('DART 로그 로드 오류:', error);
        if (elements.dartLogs) {
            elements.dartLogs.innerHTML = '<div class="log-entry error">로그 로드 중 오류가 발생했습니다.</div>';
        }
    }
}

// DART 로그 렌더링
function renderDartLogs(logs) {
    if (!elements.dartLogs) {
        console.warn('DART 로그 컨테이너를 찾을 수 없습니다.');
        return;
    }

    if (!logs || logs.length === 0) {
        elements.dartLogs.innerHTML = '<div class="log-entry info">로그가 없습니다.</div>';
        return;
    }

    const logsHtml = logs.map(log => {
        const timestamp = new Date(log.timestamp).toLocaleString('ko-KR');
        const levelClass = log.level.toLowerCase();
        return `<div class="log-entry ${levelClass}">[${timestamp}] ${log.message}</div>`;
    }).join('');
    
    elements.dartLogs.innerHTML = logsHtml;
    
    // 스크롤을 맨 위로 (최신 로그가 위에 오도록)
    elements.dartLogs.scrollTop = 0;
}

// 전체 새로고침
async function refreshAll() {
    try {
        utils.showLoading(true);
        
        // 모든 데이터 새로고침
        await Promise.allSettled([
            updateSystemStatus(),
            loadCompanies(),
            loadKeywords(),
            loadDartLogs()
        ]);
        
        utils.showAlert('전체 새로고침 완료');
    } catch (error) {
        console.error('전체 새로고침 오류:', error);
        utils.showAlert('전체 새로고침 중 오류가 발생했습니다.');
    } finally {
        utils.showLoading(false);
    }
}

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', initialize);