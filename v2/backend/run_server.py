"""
V2 Investment Monitor - 개발 서버 실행 스크립트
python run_server.py로 실행
"""
import uvicorn
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import settings

if __name__ == "__main__":
    print("V2 Investment Monitor Starting")
    print(f"Environment: {'Development' if settings.debug else 'Production'}")
    print(f"Address: http://{settings.host}:{settings.port}")
    print(f"API Docs: http://{settings.host}:{settings.port}/docs")
    print("-" * 50)
    
    # 개발용 설정
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=True,
        reload_dirs=["app"] if settings.debug else None,
        reload_includes=["*.py"] if settings.debug else None
    )