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
    def download_update(cls, download_url, target_filename="monster_update.zip"):
        """[브릿지 구현] 공통 라이브러리 스트리밍 다운로드 연동"""
        try:
            import re
            build_type = getattr(config, 'BUILD_TYPE', 'PRO')
            
            # 만약 앱이 TRIAL 빌드라면, Pro.zip을 Trial.zip으로 변경해서 다운로드.
            if build_type == "TRIAL":
                download_url = download_url.replace("Pro.zip", "Trial.zip")
            elif build_type == "PRO":
                download_url = download_url.replace("Trial.zip", "Pro.zip")
                
            if not os.path.isabs(target_filename):
                target_filename = os.path.join(config.LOCAL_BASE_PATH, target_filename)

            logger.info(f"📥 업데이트 다운로드 시작: {download_url} -> {target_filename}")
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
            
            extracted_folder = None
            extracted_exe_name = None
            
            # ZIP 압축 해제 처리 (압축된 배포일 경우)
            if update_package_path.endswith('.zip'):
                import zipfile
                logger.info("📦 압축 해제 중...")
                with zipfile.ZipFile(update_package_path, 'r') as zip_ref:
                    # zip 파일 내부의 최상위 폴더 이름 동적 탐지
                    top_levels = set([name.split('/')[0] for name in zip_ref.namelist() if '/' in name])
                    if top_levels:
                        extracted_folder = list(top_levels)[0]
                        extracted_exe_name = f"{extracted_folder}.exe"
                    
                    zip_ref.extractall(app_dir)
                os.remove(update_package_path)
            
            if not extracted_folder or not extracted_exe_name:
                logger.error("업데이트 패키지 내 구조를 분석할 수 없습니다.")
                return False
            
            # 배치 파일 내용 생성 (기존 폴더/파일 백업 후 통째로 이동)
            bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
taskkill /f /im "{os.path.basename(current_exe)}" > nul 2>&1
taskkill /f /im "NPlace-DB-*.exe" > nul 2>&1
taskkill /f /im "Map_DB-*.exe" > nul 2>&1
timeout /t 1 /nobreak > nul

if exist "{app_dir}\\_internal" rmdir /s /q "{app_dir}\\_internal"
xcopy /E /Y /C /Q "{os.path.join(app_dir, extracted_folder, '*')}" "{app_dir}\\"
rmdir /s /q "{os.path.join(app_dir, extracted_folder)}"
del /q "{app_dir}\\NPlace-DB-*.exe" 2>nul
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
