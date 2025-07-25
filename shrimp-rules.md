# V2 Investment Monitor - AI Agent Development Guidelines

## Project Overview

**Project Name**: Investment Monitor V2
**Location**: C:\2dept\v2
**Technology Stack**: FastAPI + React + TypeScript + WebSocket
**Purpose**: DART disclosure monitoring + Stock price tracking web application

### Core Architecture
```
v2/
├── backend/          # FastAPI + SQLAlchemy + WebSocket
│   ├── app/main.py  # Application entry point
│   ├── core/        # Configuration & database
│   ├── services/    # Business logic (dart_service, stock_service)
│   ├── routers/     # API endpoints
│   └── models/      # Data models
└── frontend/        # React + Vite + TypeScript
    ├── src/App.tsx  # Main application
    ├── components/  # UI components
    ├── pages/       # Page components
    ├── hooks/       # Custom hooks (useWebSocket)
    └── stores/      # Zustand state management
```

## Mandatory File Coordination Rules

### **Rule 1: WebSocket Message Types**
- **When**: Adding new WebSocket message types
- **Backend**: Update `app/services/websocket_service.py` message handlers
- **Frontend**: Update `src/types/index.ts` type definitions
- **Format**: All messages MUST follow `{"type": "...", "data": {...}}` structure

### **Rule 2: API Endpoint Changes**
- **When**: Modifying API endpoints in `app/routers/`
- **Must also update**: `frontend/src/services/apiClient.ts`
- **Must also update**: Frontend TypeScript types in `src/types/`
- **Must maintain**: Consistent error response format

### **Rule 3: Service Layer Updates**
- **When**: Modifying `app/services/dart_service.py` or `app/services/stock_service.py`
- **Must also check**: Corresponding router in `app/routers/`
- **Must also check**: Database models in `app/models/`
- **Must maintain**: Background task compatibility in `app/main.py`

### **Rule 4: Database Schema Changes**
- **When**: Modifying any model in `app/models/`
- **Must update**: Service layer methods
- **Must update**: API response schemas
- **Must create**: Database migration if needed
- **Must test**: All CRUD operations

## Critical Backend Rules

### **Error Handling Standards**
```python
# REQUIRED pattern for all API endpoints
try:
    result = await service_method()
    return {"status": "success", "data": result}
except SpecificException as e:
    logger.error(f"[ERROR] Operation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

### **Logging Requirements**
- **Use**: `logger.info()` for normal operations
- **Use**: `logger.error()` for errors
- **Format**: `[SERVICE] Description` for service logs
- **Location**: All logs MUST be saved to `C:\2dept\logs`

### **Background Task Rules**
- **NEVER** modify task scheduling in `app/main.py` without testing
- **ALWAYS** use `try-except` in background tasks
- **REQUIRED** graceful shutdown handling
- **CRITICAL** tasks: `dart_monitoring_task`, `stock_monitoring_task`

## Frontend Development Rules

### **State Management**
- **Global state**: Use Zustand store in `src/stores/appStore.ts`
- **Server state**: Use React Query for API calls
- **WebSocket state**: Use custom `useWebSocket` hook
- **Local state**: Use React useState for component-specific data

### **Component Organization**
```typescript
// REQUIRED structure for page components
function PageComponent() {
  const { data, isLoading, error } = useQuery(...)
  const { isConnected } = useWebSocket()
  
  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error} />
  
  return (
    <div className="p-6">
      {/* Page content */}
    </div>
  )
}
```

### **TypeScript Requirements**
- **MUST** define interfaces in `src/types/index.ts`
- **MUST** use proper typing for all API responses
- **MUST** type WebSocket message payloads
- **AVOID** using `any` type

## Testing Priority System

### **Level 1: Infrastructure Tests (FIRST)**
1. Database connection: `python -c "from app.core.database import check_database_health; print(check_database_health())"`
2. Environment variables: Check `.env` file exists and has required values
3. File structure: Verify all required directories exist
4. Dependencies: Run `pip install -r requirements.txt` and `npm install`

### **Level 2: Backend Service Tests**
1. FastAPI server start: `cd v2/backend && python app/main.py`
2. Health endpoint: `curl http://localhost:8000/health`
3. WebSocket connection: Test `/ws` endpoint
4. Background tasks: Check logs for task execution

### **Level 3: Frontend Integration Tests**
1. React app build: `cd v2/frontend && npm run dev`
2. API communication: Test frontend → backend calls
3. WebSocket client: Verify real-time updates
4. Page rendering: Check all routes work

### **Level 4: Business Logic Tests**
1. DART service: Test disclosure fetching
2. Stock service: Test PyKrx integration
3. Notification system: Test alert delivery
4. Data persistence: Verify database operations

## Absolute Prohibitions

### **🚫 NEVER DO**
- Hardcode API keys, passwords, or sensitive data in source code
- Modify WebSocket connection logic without thorough testing
- Delete or rename existing v1 files (`dart_monitor.py`, `simple_stock_manager_integrated.py`)
- Change database schema without backup
- Modify background task intervals without understanding market hours
- Use `localStorage` in React components (use Zustand store instead)
- Deploy with `debug=True` in production
- Ignore CORS settings for security

### **⚠️ CRITICAL DEPENDENCIES**
- **PyKrx**: Korean stock data only, no alternatives
- **Market Hours**: Stock updates only during trading hours (9:00-15:30 KST)
- **WebSocket**: Core communication channel, changes affect entire system
- **SQLite**: Current database, PostgreSQL migration planned

## Development Environment Standards

### **Port Assignments**
- Backend (FastAPI): `localhost:8000`
- Frontend (Vite): `localhost:3000`
- Database: SQLite file-based
- WebSocket: `ws://localhost:8000/ws`

### **File Modification Workflow**
1. **ALWAYS** read the file content before editing
2. **REQUIRED** use `edit-file-lines` with `dryRun: true` first
3. **MUST** test changes before git commit
4. **REQUIRED** update related files (see coordination rules)
5. **MUST** check logs after any service changes

### **Git Workflow**
1. Work in `test` branch for experimental changes
2. Test thoroughly before merging to `master`
3. Commit message format: `feat:`, `fix:`, `test:`, `chore:`
4. **ALWAYS** add files before commit: `git add .`

## Error Resolution Guidelines

### **Import/Module Errors**
- Check file paths relative to project root
- Verify `__init__.py` files exist where needed
- Check Python path includes project directory
- Review `sys.path` in problematic modules

### **WebSocket Connection Issues**
- Check CORS settings in `app/main.py`
- Verify port 8000 is available
- Test WebSocket endpoint directly
- Check firewall settings

### **Database Connection Problems**
- Verify SQLite file permissions
- Check database file location: `v2/backend/app.db`
- Test database health endpoint
- Review database initialization code

### **API Response Errors**
- Check FastAPI server logs
- Verify request payload format
- Test endpoints with curl/Postman
- Review error handling in routers

## Decision-Making Priorities

### **When Faced with Ambiguous Requirements**
1. **Maintain** existing functionality first
2. **Preserve** real-time WebSocket communication
3. **Keep** data integrity and consistency
4. **Follow** established patterns in codebase
5. **Ask** for clarification if safety is uncertain

### **Code Quality Standards**
- **Readability** over cleverness
- **Consistency** with existing code style
- **Error handling** for all external calls
- **Logging** for debugging and monitoring
- **Type safety** in TypeScript components

---

**Generated for**: AI Agent operational guidance
**Project**: Investment Monitor V2 (C:\2dept\v2)
**Last Updated**: Auto-generated during project initialization