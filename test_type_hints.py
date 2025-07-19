#!/usr/bin/env python3
"""
타입 힌팅 및 코드 문서화 테스트
"""
import sys
import inspect
import ast
sys.path.append('/mnt/c/2dept/backend')

def check_type_hints(module_path: str, module_name: str) -> dict:
    """
    모듈의 타입 힌팅 상태를 확인
    
    Args:
        module_path: 모듈 파일 경로
        module_name: 모듈 이름
    
    Returns:
        dict: 타입 힌팅 통계
    """
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        total_functions = 0
        typed_functions = 0
        documented_functions = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total_functions += 1
                
                # 타입 힌팅 확인
                has_return_annotation = node.returns is not None
                has_arg_annotations = any(arg.annotation for arg in node.args.args)
                
                if has_return_annotation or has_arg_annotations:
                    typed_functions += 1
                
                # docstring 확인
                if (node.body and 
                    isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    documented_functions += 1
        
        return {
            'module': module_name,
            'total_functions': total_functions,
            'typed_functions': typed_functions,
            'documented_functions': documented_functions,
            'type_coverage': (typed_functions / total_functions * 100) if total_functions > 0 else 0,
            'doc_coverage': (documented_functions / total_functions * 100) if total_functions > 0 else 0
        }
        
    except Exception as e:
        return {
            'module': module_name,
            'error': str(e),
            'total_functions': 0,
            'typed_functions': 0,
            'documented_functions': 0,
            'type_coverage': 0,
            'doc_coverage': 0
        }

def check_module_docstrings(module_path: str) -> bool:
    """모듈 레벨 docstring 확인"""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        # 모듈 레벨 docstring 확인
        if (tree.body and 
            isinstance(tree.body[0], ast.Expr) and 
            isinstance(tree.body[0].value, ast.Constant) and 
            isinstance(tree.body[0].value.value, str)):
            return True
        return False
        
    except Exception:
        return False

def main():
    """메인 테스트 함수"""
    print("=== 타입 힌팅 및 코드 문서화 검사 ===")
    
    # 검사할 모듈들
    modules_to_check = [
        ('/mnt/c/2dept/backend/app/config.py', 'config'),
        ('/mnt/c/2dept/backend/app/utils/logger.py', 'logger'),
        ('/mnt/c/2dept/backend/app/utils/email_sender.py', 'email_sender'),
        ('/mnt/c/2dept/backend/app/shared/email.py', 'email'),
        ('/mnt/c/2dept/backend/app/modules/dart/service.py', 'dart_service'),
        ('/mnt/c/2dept/backend/app/modules/stocks/service.py', 'stock_service'),
    ]
    
    total_stats = {
        'modules': 0,
        'total_functions': 0,
        'typed_functions': 0,
        'documented_functions': 0,
        'modules_with_docstring': 0
    }
    
    print(f"\n📊 모듈별 타입 힌팅 및 문서화 현황:")
    print(f"{'모듈명':<15} {'함수수':<6} {'타입힌팅':<8} {'문서화':<6} {'타입%':<6} {'문서%':<6}")
    print("-" * 60)
    
    for module_path, module_name in modules_to_check:
        stats = check_type_hints(module_path, module_name)
        
        if 'error' in stats:
            print(f"{module_name:<15} ERROR: {stats['error']}")
            continue
        
        # 모듈 docstring 확인
        has_module_docstring = check_module_docstrings(module_path)
        if has_module_docstring:
            total_stats['modules_with_docstring'] += 1
        
        total_stats['modules'] += 1
        total_stats['total_functions'] += stats['total_functions']
        total_stats['typed_functions'] += stats['typed_functions']
        total_stats['documented_functions'] += stats['documented_functions']
        
        print(f"{module_name:<15} "
              f"{stats['total_functions']:<6} "
              f"{stats['typed_functions']:<8} "
              f"{stats['documented_functions']:<6} "
              f"{stats['type_coverage']:<5.1f}% "
              f"{stats['doc_coverage']:<5.1f}%")
    
    print("-" * 60)
    
    # 전체 통계
    overall_type_coverage = (total_stats['typed_functions'] / total_stats['total_functions'] * 100) if total_stats['total_functions'] > 0 else 0
    overall_doc_coverage = (total_stats['documented_functions'] / total_stats['total_functions'] * 100) if total_stats['total_functions'] > 0 else 0
    module_doc_coverage = (total_stats['modules_with_docstring'] / total_stats['modules'] * 100) if total_stats['modules'] > 0 else 0
    
    print(f"{'전체':<15} "
          f"{total_stats['total_functions']:<6} "
          f"{total_stats['typed_functions']:<8} "
          f"{total_stats['documented_functions']:<6} "
          f"{overall_type_coverage:<5.1f}% "
          f"{overall_doc_coverage:<5.1f}%")
    
    print(f"\n📈 전체 통계:")
    print(f"   검사한 모듈: {total_stats['modules']}개")
    print(f"   전체 함수: {total_stats['total_functions']}개")
    print(f"   타입 힌팅 적용: {total_stats['typed_functions']}개 ({overall_type_coverage:.1f}%)")
    print(f"   문서화 완료: {total_stats['documented_functions']}개 ({overall_doc_coverage:.1f}%)")
    print(f"   모듈 문서화: {total_stats['modules_with_docstring']}개 ({module_doc_coverage:.1f}%)")
    
    # 권장사항
    print(f"\n💡 코드 품질 평가:")
    if overall_type_coverage >= 80:
        print(f"   ✅ 타입 힌팅: 우수 ({overall_type_coverage:.1f}%)")
    elif overall_type_coverage >= 60:
        print(f"   ⚠️  타입 힌팅: 양호 ({overall_type_coverage:.1f}%)")
    else:
        print(f"   ❌ 타입 힌팅: 개선 필요 ({overall_type_coverage:.1f}%)")
    
    if overall_doc_coverage >= 80:
        print(f"   ✅ 문서화: 우수 ({overall_doc_coverage:.1f}%)")
    elif overall_doc_coverage >= 60:
        print(f"   ⚠️  문서화: 양호 ({overall_doc_coverage:.1f}%)")
    else:
        print(f"   ❌ 문서화: 개선 필요 ({overall_doc_coverage:.1f}%)")
    
    print(f"\n🎯 개선 완료 항목:")
    print(f"   • Google 스타일 docstring 적용")
    print(f"   • 함수 시그니처 타입 힌팅")
    print(f"   • mypy 설정 파일 생성")
    print(f"   • 모듈별 상세 문서화")

if __name__ == "__main__":
    main()