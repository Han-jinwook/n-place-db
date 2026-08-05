# 🔱 Monster 공통 라이브러리 - updater.py
# - 버전: v1.1
# - 갱신 일시: 2026-05-18
# - 관리 주체: Monster 총괄 AI (Hub AI)

import os
import requests
import logging

logger = logging.getLogger(__name__)

class MonsterUpdater:
    """
    [3Monster Master Library] 표준 자동 업데이트 엔진
    Supabase REST API를 직접 조회하여 개별 앱의 신규 버전을 감지하고 다운로드합니다.
    """
    
    VERSION = "1.1.0"
    
    @classmethod
    def check_for_updates(cls, product_id, current_version, supabase_url=None, supabase_key=None):
        """서버에서 최신 버전을 확인하고 업데이트 정보 딕셔너리를 반환합니다."""
        url_base = supabase_url or os.getenv("SUPABASE_URL") or "https://suwinftalfgybvrnzruz.supabase.co"
        key = supabase_key or os.getenv("SUPABASE_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY") or "sb_publishable_jUwQ1BWvG6F2H9GyELUoFw_mUOHbgWD"
        
        if not url_base or not key:
            logger.error("업데이트 체크 실패: Supabase 설정 정보 누락")
            return None

        # 버전 역정렬 후 상위 1개만 조회하는 PostgREST API 쿼리
        url = f"{url_base.rstrip('/')}/rest/v1/app_versions?product_id=eq.{product_id}&order=version.desc&limit=1"
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

        try:
            # 타임아웃 5.0초로 완화 (Supabase 응답 지연 대비)
            response = requests.get(url, headers=headers, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            if data:
                latest = data[0]
                if cls._is_newer(latest['version'], current_version):
                    return {
                        "version": latest['version'],
                        "download_url": latest['download_url'],
                        "release_notes": latest.get('release_notes', '')
                    }
            return None
        except requests.exceptions.Timeout:
            logger.warning("업데이트 체크 시간 초과 (5.0초 제한)")
            return None
        except Exception as e:
            logger.error(f"업데이트 체크 중 예외 발생: {e}")
            return None

    @staticmethod
    def _is_newer(latest, current):
        """버전 문자열(예: '1.2.3')의 크기를 비교합니다."""
        try:
            return [int(p) for p in latest.split('.')] > [int(p) for p in current.split('.')]
        except Exception:
            return latest > current

    @classmethod
    def download_to(cls, download_url, save_path):
        """파일 다운로드 엔진 (대용량 패키지 스트리밍 다운로드 지원)"""
        import time
        max_retries = 3
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        abs_save_path = os.path.abspath(save_path)
        os.makedirs(os.path.dirname(abs_save_path), exist_ok=True)

        for attempt in range(max_retries):
            try:
                logger.info(f"📥 다운로드 시도 ({attempt+1}/{max_retries}): {download_url}")
                response = requests.get(download_url, headers=headers, stream=True, timeout=60.0)
                response.raise_for_status()
                with open(abs_save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                logger.info(f"✅ 다운로드 성공: {abs_save_path}")
                return True
            except Exception as e:
                logger.error(f"공통 다운로드 패치 실패 (시도 {attempt+1}/{max_retries}): {e}")
                if os.path.exists(abs_save_path):
                    try: os.remove(abs_save_path)
                    except: pass
                time.sleep(2)
        return False
