# 🔱 Monster 공통 라이브러리 연동 - updater.py (NPlace-DB)
# - 버전: v1.1
# - 갱신 일시: 2026-05-19
# - 관리 주체: Monster 총괄 AI (Hub AI)

import os
import sys
import logging
import subprocess
import requests
import config
from 라이브러리.updater import MonsterUpdater as CommonUpdater

logger = logging.getLogger(__name__)

class MonsterUpdater:
    """
    [3Monster] 표준 자동 업데이트 엔진 (공통 라이브러리 연동 브릿지 버전)
    공통 라이브러리(라이브러리.updater.MonsterUpdater)를 연동하여 
    0.5초 타임아웃 및 가벼운 requests 방식 버전 조회를 탑재하고,
    기존 앱 고유의 자가 패칭 및 재시작 프로세스를 그대로 수행합니다.
    """
    
    CURRENT_VERSION = config.CURRENT_VERSION
    PRODUCT_ID = config.PRODUCT_ID
    
    @classmethod
    def check_for_updates(cls):
        """[브릿지 구현] 공통 업데이터를 호출하여 최신 버전을 감지합니다."""
        try:
            logger.info("🔍 [라이브러리 검증] 최신 버전 확인 중...")
            
            update_info = CommonUpdater.check_for_updates(
                product_id=cls.PRODUCT_ID,
                current_version=cls.CURRENT_VERSION,
                supabase_url=config.SUPABASE_URL,
                supabase_key=config.SUPABASE_KEY
            )
            
            if update_info:
                logger.info(f"🚀 새 업데이트 발견: {cls.CURRENT_VERSION} -> {update_info['version']}")
                return update_info
            else:
                logger.info("✅ 최신 버전을 사용 중입니다.")
                return None
                
        except Exception as e:
            logger.error(f"업데이트 확인 중 오류 발생: {e}")
            return None

    @classmethod
    def download_update(cls, download_url, target_filename="update_package.zip"):
        """[브릿지 구현] 공통 라이브러리 스트리밍 다운로드 연동"""
        try:
            # BUILD_TYPE에 따라 URL 및 타겟 파일명 조정
            build_type = getattr(config, 'BUILD_TYPE', 'PRO')
            
            # download_url 은 보통 .../NPlace-DB-Pro.zip 형식으로 DB에 등록됨.
            # 만약 앱이 TRIAL 빌드라면, Pro.zip 을 Trial.zip 으로 변경해서 다운로드.
            if build_type == "TRIAL" and "Pro.zip" in download_url:
                download_url = download_url.replace("Pro.zip", "Trial.zip")
            elif build_type == "PRO" and "Trial.zip" in download_url:
                download_url = download_url.replace("Trial.zip", "Pro.zip")
                
            logger.info(f"📥 업데이트 다운로드 시작: {download_url}")
            success = CommonUpdater.download_to(download_url, target_filename)
            if success:
                logger.info(f"✅ 다운로드 완료: {target_filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"다운로드 중 오류 발생: {e}")
            return False

    @classmethod
    def apply_update_and_restart(cls, update_package_path="update_package.zip"):
        """
        다운로드된 파일을 적용하고 앱을 재시작합니다.
        (기존의 자가 패칭 배치 파일 제어 메커니즘 유지)
        """
        try:
            current_exe = sys.executable
            app_dir = os.path.dirname(current_exe)
            
            # 배치 파일 경로
            bat_path = os.path.join(app_dir, "monster_update_helper.bat")
            
            # 새 실행 파일 이름 (현재 빌드 타입에 맞춰 실행 파일 이름 추론)
            build_type = getattr(config, 'BUILD_TYPE', 'PRO')
            v = config.CURRENT_VERSION
            
            # 압축 해제 후 생성될 디렉토리 이름 예측
            extracted_folder = f"NPlace-DB-{build_type}-v{v}"
            extracted_exe_name = f"NPlace-DB-{build_type}-v{v}.exe"
            
            # 압축을 풀면 디렉토리 안에 exe가 있으므로
            new_exe = os.path.join(app_dir, extracted_folder, extracted_exe_name)
            
            # ZIP 압축 해제 처리 (압축된 배포일 경우)
            if update_package_path.endswith('.zip'):
                import zipfile
                logger.info("📦 압축 해제 중...")
                with zipfile.ZipFile(update_package_path, 'r') as zip_ref:
                    zip_ref.extractall(app_dir)
                os.remove(update_package_path)
            
            # 배치 파일 내용 생성 (기존 폴더/파일 백업 후 통째로 이동)
            bat_content = f"""@echo off
timeout /t 3 /nobreak > nul
taskkill /f /im "{os.path.basename(current_exe)}" > nul 2>&1
timeout /t 1 /nobreak > nul

xcopy /E /Y /C /Q "{os.path.join(app_dir, extracted_folder, '*')}" "{app_dir}\\"
rmdir /s /q "{os.path.join(app_dir, extracted_folder)}"
start "" "{os.path.join(app_dir, extracted_exe_name)}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="cp949") as f:
                f.write(bat_content)
                
            logger.info("🔄 업데이트 헬퍼 생성 완료. 프로세스를 종료하고 업데이트를 적용합니다.")
            subprocess.Popen([bat_path], shell=True)
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"업데이트 적용 중 오류 발생: {e}")
            return False
