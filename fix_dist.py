import sys
import os

file_path = 'd:/N-Place-DB/prepare_dist.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = next((i for i, l in enumerate(lines) if 'old_files = [' in l), -1)
end_idx = next((i for i, l in enumerate(lines) if '# [D] Copy dependencies folder' in l), -1)

if start_idx != -1 and end_idx != -1:
    new_content = """            # Remove old legacy files to prevent duplicates
            old_files = ["NPlace-DB-실행.bat", "사용방법_필독(처음 실행시 필수 확인).txt", "zip풀고 최초 1회실행.bat"]
            for old_file in old_files:
                old_file_path = os.path.join(dist_final_dir, old_file)
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                        print(f"  Removed legacy residual file: {old_file}")
                    except Exception as e:
                        print(f"  Warning removing {old_file}: {e}")

            # [A] Create Dynamic Version-Correct Batch Launcher
            launcher_path = os.path.join(dist_final_dir, "실행 오류시 최초 1회실행.bat")
            launcher_content = f\"\"\"@echo off
setlocal
title NPlace-DB Launcher

echo ======================================================
echo   NPlace-DB 시스템 자가 진단 및 기동 중...
echo ======================================================
echo.

:: 1. 필수 런타임 (Visual C++ Redistributable 2015-2022) 확인
echo [1/2] 필수 시스템 구성 요소 확인 중...
reg query "HKEY_LOCAL_MACHINE\\\\SOFTWARE\\\\Microsoft\\\\VisualStudio\\\\14.0\\\\VC\\\\Runtimes\\\\x64" /v "Installed" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 일부 시스템에서 Visual C++ 런타임이 필요할 수 있습니다.
    echo.
    echo [안내] 수동 설치 링크: https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo.
    echo (계속하려면 아무 키나 누르세요... 곧 프로그램이 실행됩니다.)
    timeout /t 3 >nul
) else (
    echo [OK] 시스템 구성 요소가 이미 설치되어 있습니다.
)

:: 2. 프로그램 실행
echo.
echo [2/2] 프로그램을 실행하는 중입니다...

if exist "NPlace-DB-v{v}.exe" (
    start "" "NPlace-DB-v{v}.exe"
) else (
    echo [오류] 실행 파일을 찾을 수 없습니다.
    echo 폴더 구성을 확인해 주세요.
    pause
    exit /b 1
)

echo [OK] 완료! 이 창은 3초 후 자동으로 닫힙니다.
timeout /t 3 >nul
exit
\"\"\"
            with open(launcher_path, "w", encoding="euc-kr") as lf:
                lf.write(launcher_content)
            print("  Created: 실행 오류시 최초 1회실행.bat")

            # [B] Copy docs/ folder (clean documents)
            dist_docs_dir = os.path.join(dist_final_dir, "docs")
            if os.path.exists(dist_docs_dir):
                import shutil
                shutil.rmtree(dist_docs_dir)
            import shutil
            shutil.copytree(os.path.join(root_dir, "docs"), dist_docs_dir)
            print("  Copied: docs/ folder")

            # [C] Create Clean 사용전_필독.txt pointing to in-app guide and simplified tips
            readme_path = os.path.join(dist_final_dir, "사용전_필독.txt")
            readme_content = f\"\"\"======================================================
🎯 N-Place-DB Pro 사용 전 필수 확인 (v{v})
======================================================

안전하고 원활한 실행을 위해 아래 딱 3가지만 확인해주세요!

1. 📂 [바탕화면에 압축 풀기]
   - 다운로드한 ZIP 파일은 반드시 [바탕화면]이나 [C드라이브 루트]에 풀어주세요.
   ⚠️ 주의: C:\\\\Program Files 폴더 밑에 풀면 실행 권한 오류가 발생합니다.

2. 🚀 [프로그램 실행 방법]
   - 폴더 내의 [ NPlace-DB-v{v}.exe ]를 더블클릭하여 바로 실행하시면 됩니다.
   ⚠️ 만약 실행 시 "VCRUNTIME140.dll 누락" 등 시스템 오류창이 뜬다면,
      옆에 있는 [ 실행 오류시 최초 1회실행.bat ] 파일을 가동하여 10초 만에 해결하시면 됩니다.

3. 🛡️ [백신 오진 대처법]
   - 본 마케팅 도구 실행 시 윈도우 디펜더/V3/알약 등이 바이러스로 오진하여 차단할 수 있습니다.
   - 실행이 안 되거나 파일이 지워질 경우, 해당 백신 실시간 감시를 잠시 끄시거나 
     [검사 예외 대상 설정] 메뉴에서 압축을 푼 폴더 전체를 예외 등록해주세요.

※ 상세 마케팅 노하우 및 기능 꿀팁은 대시보드 내의 [📖 가이드] 탭에 고스란히 담겨 있습니다!
======================================================
\"\"\"
            with open(readme_path, "w", encoding="utf-8-sig") as rf:
                rf.write(readme_content)
            print("  Created: 사용전_필독.txt")

"""
    new_lines = lines[:start_idx] + [new_content] + lines[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Fixed successfully!")
else:
    print(f"Could not find boundaries. start: {start_idx}, end: {end_idx}")
