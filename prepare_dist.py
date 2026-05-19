import os
import shutil
import json
import glob
import config

def cleanup():
    v = config.CURRENT_VERSION
    print(f"[Cleanup] N-Place-DB Pro (v{v}) distribution packing and zip started...")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Clear Logs
    print("- Deleting log files...")
    for log_file in glob.glob(os.path.join(root_dir, "*.log")):
        try:
            os.remove(log_file)
            print(f"  Deleted: {os.path.basename(log_file)}")
        except Exception as e:
            print(f"  Error deleting {log_file}: {e}")

    # 2. Clear Database & License
    print("- Deleting local DB and checkpoint (Clean distribution)...")
    db_file = os.path.join(root_dir, "data", "database.sqlite")
    checkpoint_file = os.path.join(root_dir, "crawler_checkpoint.json")
    
    for f in [db_file, checkpoint_file]:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"  Deleted: {os.path.basename(f)}")
            except Exception as e:
                print(f"  Error deleting {f}: {e}")

    # 3. Clear Browser Sessions
    print("- Wiping browser session info...")
    session_dir = os.path.join(root_dir, "messenger", "browser_session")
    if os.path.exists(session_dir):
        try:
            shutil.rmtree(session_dir)
            os.makedirs(session_dir)
            print("  Wiped: browser_session/")
        except Exception as e:
            print(f"  Error wiping sessions: {e}")

    # 4. Clear Exports & CSV Data
    print("- Wiping exports folder and CSV files...")
    exports_dir = os.path.join(root_dir, "exports")
    if os.path.exists(exports_dir):
        try:
            shutil.rmtree(exports_dir)
            os.makedirs(exports_dir)
            print("  Wiped: exports/")
        except Exception as e:
            print(f"  Error wiping exports: {e}")
            
    # Delete specific CSVs that might be in root
    csv_patterns = [
        "확장_*.csv",
        "raw_shops_*.csv",
        "enriched_*.csv",
        "final_*.csv",
        "crawl_audit.csv"
    ]
    for pattern in csv_patterns:
        for f in glob.glob(os.path.join(root_dir, pattern)):
            try:
                os.remove(f)
                print(f"  Deleted: {os.path.basename(f)}")
            except: pass

    # 5. Reset Templates (Personal Credentials for Security)
    print("- Resetting template and credential configs...")
    tpl_path = os.path.join(root_dir, "admin_dashboard", "templates.json")
    if os.path.exists(tpl_path):
        default_tpl = {
            "tpl_A": {
                "subject": "[제안] 비즈니스 협업 제안드립니다.",
                "body": "안녕하세요 {상호명} 원장님,\n\n협업 제안 드립니다..."
            },
            "tpl_C": "안녕하세요 {상호명} 원장님, 메시지 드립니다!",
            "email_user": "",
            "email_pw": "",
            "insta_user": "",
            "insta_pw": ""
        }
        try:
            with open(tpl_path, "w", encoding="utf-8") as f:
                json.dump(default_tpl, f, ensure_ascii=False, indent=4)
            print("  Reset: templates.json")
        except Exception as e:
            print(f"  Error resetting templates: {e}")

    # 6. Clear Python Cache
    print("- Cleaning Python pycache folders...")
    for pycache in glob.glob(os.path.join(root_dir, "**/__pycache__"), recursive=True):
        try:
            shutil.rmtree(pycache)
        except: pass
    print("  Cleaned: __pycache__")
    
    # 7. Package Compiled Folder in dist/
    dist_folder_name = f"NPlace-DB-v{v}"
    dist_final_dir = os.path.join(root_dir, "dist", dist_folder_name)
    
    if os.path.exists(dist_final_dir):
        try:
            print(f"- Copying and writing dist files into: {dist_folder_name}...")
            
            # [A] Create Dynamic Version-Correct Batch Launcher
            launcher_path = os.path.join(dist_final_dir, "zip풀고 최초 1회실행.bat")
            launcher_content = f"""@echo off
setlocal
title NPlace-DB Launcher

echo ======================================================
echo   NPlace-DB 시스템 자가 진단 및 기동 중...
echo ======================================================
echo.

:: 1. 필수 런타임 (Visual C++ Redistributable 2015-2022) 확인
echo [1/2] 필수 시스템 구성 요소 확인 중...
reg query "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\VisualStudio\\14.0\\VC\\Runtimes\\x64" /v "Installed" >nul 2>&1
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
"""
            with open(launcher_path, "w", encoding="euc-kr") as lf:
                lf.write(launcher_content)
            print("  Created: zip풀고 최초 1회실행.bat")

            # [B] Copy docs/ folder (clean documents)
            dist_docs_dir = os.path.join(dist_final_dir, "docs")
            if os.path.exists(dist_docs_dir):
                shutil.rmtree(dist_docs_dir)
            shutil.copytree(os.path.join(root_dir, "docs"), dist_docs_dir)
            print("  Copied: docs/ folder")

            # [C] Create Clean 사용전_필독.txt pointing to in-app guide and simplified tips
            readme_path = os.path.join(dist_final_dir, "사용전_필독.txt")
            readme_content = f"""======================================================
🎯 N-Place-DB Pro 사용 전 필수 확인 (v{v})
======================================================

안전하고 원활한 실행을 위해 아래 딱 3가지만 확인해주세요!

1. 📂 [바탕화면에 압축 풀기]
   - 다운로드한 ZIP 파일은 반드시 [바탕화면]이나 [C드라이브 루트]에 풀어주세요.
   ⚠️ 주의: C:\\Program Files 폴더 밑에 풀면 실행 권한 오류가 발생합니다.

2. 🚀 [프로그램 실행 방법]
   - 폴더 내의 [ NPlace-DB-v{v}.exe ]를 더블클릭하여 바로 실행하시면 됩니다.
   ⚠️ 만약 실행 시 "VCRUNTIME140.dll 누락" 등 시스템 오류창이 뜬다면,
      옆에 있는 [ zip풀고 최초 1회실행.bat ] 파일을 가동하여 10초 만에 해결하시면 됩니다.

3. 🛡️ [백신 오진 대처법]
   - 본 마케팅 도구 실행 시 윈도우 디펜더/V3/알약 등이 바이러스로 오진하여 차단할 수 있습니다.
   - 실행이 안 되거나 파일이 지워질 경우, 해당 백신 실시간 감시를 잠시 끄시거나 
     [검사 예외 대상 설정] 메뉴에서 압축을 푼 폴더 전체를 예외 등록해주세요.

※ 상세 마케팅 노하우 및 기능 꿀팁은 대시보드 내의 [📖 가이드] 탭에 고스란히 담겨 있습니다!
======================================================
"""
            with open(readme_path, "w", encoding="utf-8-sig") as rf:
                rf.write(readme_content)
            print("  Created: 사용전_필독.txt")

            # [D] Copy dependencies folder
            dep_src = os.path.join(root_dir, "dependencies")
            dep_target = os.path.join(dist_final_dir, "dependencies")
            if os.path.exists(dep_src):
                if os.path.exists(dep_target):
                    shutil.rmtree(dep_target)
                shutil.copytree(dep_src, dep_target)
                print("  Copied: dependencies/ folder")
            
            # 8. [ZIP ARCHIVE] Automatically Compress to .zip
            print(f"- Compressing distribution folder into: dist/{dist_folder_name}.zip...")
            zip_out_path = os.path.join(root_dir, "dist", dist_folder_name)
            shutil.make_archive(
                base_name=zip_out_path,
                format="zip",
                root_dir=os.path.join(root_dir, "dist"),
                base_dir=dist_folder_name
            )
            print(f"[Success] ZIP compression complete! Final package: dist/{dist_folder_name}.zip")
            
        except Exception as e:
            print(f"[Error] Error during packaging: {e}")
    else:
        print(f"[Error] Compiled build directory dist/{dist_folder_name} not found. Please run build_exe.py first.")

if __name__ == "__main__":
    cleanup()
