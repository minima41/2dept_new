import sys
import os

# 백엔드 디렉토리를 파이썬 경로에 추가
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

# 현재 작업 디렉토리를 백엔드로 변경
os.chdir(backend_path)

# FastAPI 앱 실행
from app.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)