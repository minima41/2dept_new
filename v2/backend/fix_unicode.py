#!/usr/bin/env python3
"""
Script to fix Unicode issues in the V2 Investment Monitor backend
Replaces emoji and Korean text in log messages with ASCII equivalents
"""
import os
import re
from pathlib import Path

# Unicode replacements
REPLACEMENTS = {
    # Emojis
    '🚀': '[START]',
    '✅': '[SUCCESS]',
    '❌': '[ERROR]',
    '⚠️': '[WARNING]',
    '🔔': '[NOTIFICATION]',
    '📧': '[EMAIL]',
    '📈': '[STOCK]',
    '📋': '[DART]',
    '🔄': '[PROCESS]',
    '🔌': '[CONNECTION]',
    '📡': '[BROADCAST]',
    '🗄️': '[DATABASE]',
    '🌐': '[WEB]',
    '🚨': '[CRITICAL]',
    
    # Korean text
    ' 시작': ' starting',
    ' 종료': ' stopping',
    ' 완료': ' completed',
    ' 실패': ' failed',
    ' 중...': ' in progress...',
    ' 중단': ' stopped',
    ' 확인': ' checking',
    ' 조회': ' querying',
    ' 업데이트': ' updating',
    ' 처리': ' processing',
    ' 발송': ' sending',
    ' 생성': ' creating',
    ' 연결': ' connected',
    ' 해제': ' disconnected',
    ' 브로드캐스트': ' broadcast',
    ' 사이클': ' cycle',
    ' 성공': ' success',
    ' 오류': ' error',
    ' 경고': ' warning',
    ' 정보': ' info',
    ' 메시지': ' message',
    ' 치명적': ' critical',
    ' 작업': ' task',
    '개': ' items',
    '건': ' records',
    '초': ' seconds',
    '분': ' minutes',
    '시간': ' hours',
}

def fix_file(file_path):
    """Fix Unicode issues in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply replacements
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all Python files in the app directory"""
    app_dir = Path(__file__).parent / "app"
    
    if not app_dir.exists():
        print(f"App directory not found: {app_dir}")
        return
    
    fixed_count = 0
    total_count = 0
    
    # Find all Python files
    for py_file in app_dir.rglob("*.py"):
        total_count += 1
        if fix_file(py_file):
            fixed_count += 1
    
    print(f"\nSummary: Fixed {fixed_count} out of {total_count} files")

if __name__ == "__main__":
    main()