/**
 * DART 공시 관리 페이지 - JavaScript
 * Flask 백엔드 API와 연동하여 DART 모니터링 시스템 관리
 */

// 전역 변수
const API_BASE = '';
let refreshInterval;

// DOM 요소 참조
const elements = {
    // 상태 표시
    dartStatus: document.getElementById('dart-status'),
    
    // 통계 카드
    companiesCount: document.getElementById('companies-count'),
    keywordsCount: document.getElementById('keywords-count'),
    disclosuresToday: document.getElementById('disclosures-today'),
    processedCount: document.getElementById('processed-count'),
    
    // 리스트 컨테이너
    companiesList: document.getElementById('companies-list'),
    keywordsList: document.getElementById('keywords-list'),
    sectionsList: document.getElementById('sections-list'),
    disclosuresList: document.getElementById('disclosures-list'),
    
    // 버튼들
    refreshCompanies: document.getElementById('refresh-companies'),
    refreshKeywords: document.getElementById('refresh-keywords'),
    refreshDisclosures: document.getElementById('refresh-disclosures'),
    manualCheck: document.getElementById('manual-check'),
    
    // 필터
    companyFilter: document.getElementById('company-filter'),
    dateFilter: document.getElementById('date-filter'),
    
    // 시스템 정보
    lastCheckTime: document.getElementById('last-check-time')
};

// API 호출 함수들
const api = {
    async getStatus() {
        const response = await fetch(`${API_BASE}/api/status`);
        return await response.json();
    },
    
    async getCompanies() {
        const response = await fetch(`${API_BASE}/api/dart/companies`);
        return await response.json();
    },
    
    async getKeywords() {
        const response = await fetch(`${API_BASE}/api/dart/keywords`);
        return await response.json();
    },
    
    async getDisclosures(filters = {}) {
        const params = new URLSearchParams();
        if (filters.date) params.append('date', filters.date);
        if (filters.company) params.append('company', filters.company);
        if (filters.limit) params.append('limit', filters.limit);
        
        const response = await fetch(`${API_BASE}/api/dart/disclosures?${params}`);
        return await response.json();
    },
    
    async manualCheck() {
        const response = await fetch(`${API_BASE}/api/dart/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        return await response.json();
    },
    
    async getProcessedIds() {
        const response = await fetch(`${API_BASE}/api/dart/processed-ids`);
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
    
    showAlert(message, type = 'info') {
        // 간단한 알림 표시 (나중에 toast 라이브러리로 교체 가능)
        alert(message);
    },
    
    showLoading(show = true) {
        document.body.style.cursor = show ? 'wait' : 'default';
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
        <div class="company-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4>${company.name}</h4>
                    <p style="color: #666; margin: 0;">${company.code}</p>
                </div>
                <div class="status-indicator ${company.enabled ? 'active' : 'inactive'}">
                    <i class="fas fa-circle"></i>
                </div>
            </div>
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
            `<span class="keyword-chip">${keyword}</span>`
        ).join('');
        elements.keywordsList.innerHTML = keywordsHtml;
    }
    
    // 중요 섹션
    if (data.important_sections && data.important_sections.length > 0) {
        const sectionsHtml = data.important_sections.map(section => 
            `<span class="keyword-chip">${section}</span>`
        ).join('');
        elements.sectionsList.innerHTML = sectionsHtml;
    }
    
    elements.keywordsCount.textContent = data.keyword_count || 0;
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
        utils.showLoading(true);
        const result = await api.getCompanies();
        
        if (result.success) {
            renderCompanies(result.companies);
            updateCompanyFilter(result.companies);
        } else {
            utils.showAlert('기업 목록 로드 실패: ' + result.error);
        }
    } catch (error) {
        console.error('기업 목록 로드 오류:', error);
        utils.showAlert('기업 목록 로드 중 오류가 발생했습니다.');
    } finally {
        utils.showLoading(false);
    }
}

async function loadKeywords() {
    try {
        utils.showLoading(true);
        const result = await api.getKeywords();
        
        if (result.success) {
            renderKeywords(result);
        } else {
            utils.showAlert('키워드 목록 로드 실패: ' + result.error);
        }
    } catch (error) {
        console.error('키워드 목록 로드 오류:', error);
        utils.showAlert('키워드 목록 로드 중 오류가 발생했습니다.');
    } finally {
        utils.showLoading(false);
    }
}

async function loadDisclosures() {
    try {
        utils.showLoading(true);
        
        const filters = {
            limit: 50
        };
        
        if (elements.companyFilter.value) {
            filters.company = elements.companyFilter.value;
        }
        
        if (elements.dateFilter.value) {
            // YYYY-MM-DD를 YYYYMMDD로 변환
            filters.date = elements.dateFilter.value.replace(/-/g, '');
        }
        
        const result = await api.getDisclosures(filters);
        
        if (result.success) {
            renderDisclosures(result.disclosures);
        } else {
            utils.showAlert('공시 목록 로드 실패: ' + result.error);
            renderDisclosures([]);
        }
    } catch (error) {
        console.error('공시 목록 로드 오류:', error);
        utils.showAlert('공시 목록 로드 중 오류가 발생했습니다.');
        renderDisclosures([]);
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

// 수동 공시 확인
async function performManualCheck() {
    try {
        utils.showLoading(true);
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
    // 새로고침 버튼들
    elements.refreshCompanies.addEventListener('click', loadCompanies);
    elements.refreshKeywords.addEventListener('click', loadKeywords);
    elements.refreshDisclosures.addEventListener('click', loadDisclosures);
    
    // 수동 확인 버튼
    elements.manualCheck.addEventListener('click', performManualCheck);
    
    // 필터 변경
    elements.companyFilter.addEventListener('change', loadDisclosures);
    elements.dateFilter.addEventListener('change', loadDisclosures);
}

// 초기화 함수
async function initialize() {
    console.log('DART 관리 페이지 초기화 시작');
    
    // 이벤트 리스너 설정
    setupEventListeners();
    
    // 오늘 날짜를 기본값으로 설정
    const today = new Date().toISOString().split('T')[0];
    elements.dateFilter.value = today;
    
    // 초기 데이터 로드
    await Promise.all([
        updateSystemStatus(),
        loadCompanies(),
        loadKeywords(),
        loadDisclosures(),
        loadProcessedIds()
    ]);
    
    // 주기적 업데이트 설정 (30초마다)
    refreshInterval = setInterval(async () => {
        await updateSystemStatus();
    }, 30000);
    
    console.log('DART 관리 페이지 초기화 완료');
}

// 페이지 언로드 시 인터벌 정리
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', initialize);