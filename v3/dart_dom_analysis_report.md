# DART DOM 구조 분석 보고서

## 분석 날짜: 2025-07-31

## 문제 상황
- SPA 환경에서 dart.js가 index.html의 dart-content 영역에서 필요한 DOM 요소들을 찾지 못함
- dart.js 초기화 시 17개 DOM 요소 누락으로 이벤트 리스너 설정 실패

## dart.js가 참조하는 22개 DOM 요소 목록

### ✅ 현재 index.html에 존재하는 요소 (5개)
1. `add-company` - 기업 추가 버튼
2. `company-filter` - 기업 필터 선택박스
3. `date-filter` - 날짜 필터 입력
4. `companies-list` - 기업 목록 컨테이너
5. (참고: index.html에는 `total-companies`, `today-disclosures`, `last-dart-check`가 있지만 dart.js는 다른 ID를 찾음)

### ❌ 누락된 요소 (17개)
1. `dart-status` - DART 모니터링 상태 표시
2. `last-check-time` - 마지막 확인 시간 (index.html의 `last-dart-check`와 다름)
3. `companies-count` - 기업 수 표시 (index.html의 `total-companies`와 다름)
4. `keywords-list` - 키워드 목록 컨테이너
5. `keywords-count` - 키워드 수 표시
6. `sections-list` - 섹션 목록 컨테이너
7. `disclosures-list` - 공시 목록 컨테이너 (index.html의 `dart-list`와 다름)
8. `disclosures-today` - 오늘 공시 수 (index.html의 `today-disclosures`와 다름)
9. `processed-count` - 처리된 공시 수
10. `refresh-companies` - 기업 목록 새로고침 버튼
11. `refresh-keywords` - 키워드 새로고침 버튼
12. `refresh-disclosures` - 공시 새로고침 버튼
13. `refresh-logs` - 로그 새로고침 버튼
14. `refresh-all` - 전체 새로고침 버튼
15. `manual-check` - 수동 확인 버튼
16. `add-keyword` - 키워드 추가 버튼
17. `log-hours` - 로그 시간 필터 선택박스
18. `dart-logs` - 로그 컨테이너

## dart.html vs index.html 구조 차이점

### 통계 카드 섹션
- **dart.html**: `companies-count`, `keywords-count`, `disclosures-today`, `processed-count`
- **index.html**: `total-companies`, `today-disclosures`, `last-dart-check`
- **문제**: ID 불일치로 dart.js가 요소를 찾지 못함

### 관리 버튼 섹션
- **dart.html**: 각 패널별로 분산된 관리 버튼들
- **index.html**: 일부 버튼만 section-controls에 집중
- **문제**: refresh-companies, add-keyword 등 다수 버튼 누락

### 로그 시스템
- **dart.html**: 완전한 로그 패널 구조 (log-hours, dart-logs)
- **index.html**: 로그 시스템 완전 누락
- **문제**: 실시간 로그 모니터링 기능 사용 불가

### 데이터 리스트
- **dart.html**: keywords-list, sections-list, disclosures-list
- **index.html**: companies-list만 존재, 나머지 누락
- **문제**: 키워드 및 섹션 관리 기능 사용 불가

## 해결 전략

### Phase 1: 통계 카드 섹션 통합
- companies-count, keywords-count, disclosures-today, processed-count 추가

### Phase 2: 관리 버튼 통합
- refresh-companies, refresh-keywords, refresh-disclosures, refresh-logs, refresh-all, manual-check, add-keyword 추가

### Phase 3: 로그 시스템 통합
- log-hours, dart-logs, last-check-time 추가

### Phase 4: 데이터 리스트 통합
- keywords-list, sections-list, disclosures-list 추가

### Phase 5: CSS 스타일 통합
- dart.html 전용 스타일을 style.css에 통합

### Phase 6: 기능 테스트
- 전체 DART 기능 정상 작동 검증

## CSS 클래스 충돌 가능성

### 안전한 클래스들
- Bootstrap 기본 클래스: `btn`, `btn-primary`, `form-control` 등
- 기존 index.html 클래스: `stat-card`, `panel-content` 등

### 주의 필요한 클래스들
- dart.html 전용 클래스: `items-list`, `logs-container`, `dart-table`
- 네임스페이스 적용 필요: `.dart-` prefix 사용 권장

## 작업 완료 기준
1. dart.js 콘솔에서 모든 22개 DOM 요소가 성공적으로 로드됨
2. "❌ 누락된 DOM 요소" 메시지가 0개가 됨
3. SPA 탭 전환 시 DART 기능이 완전히 작동함
4. 브라우저 콘솔에 JavaScript 에러가 발생하지 않음
