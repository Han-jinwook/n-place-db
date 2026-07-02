import hashlib
import os
import uuid
import logging
import requests
import threading
from datetime import datetime, timedelta, timezone
import config
from crawler.local_db_handler import LocalDBHandler
from 라이브러리.auth import MonsterAuth

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseAuthManager:
    """
    [3Monster] 수파베이스 기반 라이선스 인증 매니저 (공통 라이브러리 연동 브릿지 버전)
    공통 라이브러리(라이브러리.auth.MonsterAuth)를 내부 연동하여 0.5초 타임아웃 및 
    경량화를 실현하고, 기존 개별 앱의 로컬 라이선스 파일 보존 메커니즘을 동일하게 유지합니다.
    """
    
    LICENSE_FILE = os.path.join(config.USER_SETTINGS_PATH, "license.dat")
    # [NEW] 실시간 체험판 동기화 변수
    _trial_baseline = 0
    _trial_session_max = 0
    _trial_lock = threading.Lock()
    _collection_limit = None
    _serial_key = None

    @staticmethod
    def get_hwid() -> str:
        """기기 고유 식별자(HWID)를 정밀 산출합니다. (라이브러리/auth.py 표준 로직과 연동)"""
        try:
            # 일관된 매핑을 위해 MonsterAuth의 HWID 추출 함수 간접 호출 또는 동일 로직 구성
            auth_temp = MonsterAuth(product_id=config.PRODUCT_ID, license_key="")
            return auth_temp._get_hwid()
        except Exception as e:
            logger.error(f"Error extracting HWID: {e}")
            return "UNKNOWN_HWID"

    @classmethod
    def validate_and_bind_key(cls, key: str) -> tuple[bool, str]:
        """[브릿지 구현] 공통 MonsterAuth를 통한 실시간 수파베이스 인증 및 바인딩"""
        try:
            logger.info(f"🔍 [라이브러리 검증] 시리얼 키: {key}")
            
            # 공통 라이브러리 인스턴스 생성 및 검증 위임
            auth = MonsterAuth(
                product_id=config.PRODUCT_ID, 
                license_key=key, 
                supabase_url=config.SUPABASE_URL, 
                supabase_key=config.SUPABASE_KEY
            )
            
            success, msg, collection_limit = auth.verify_license()
            
            if success:
                cls._serial_key = key
                cls._collection_limit = collection_limit
                cls.save_local_license(key)
                logger.info(f"✅ 라이선스 인증 성공 (제한: {collection_limit}건)")
                return True, "인증 성공"
            else:
                logger.warning(f"❌ 라이선스 인증 실패: {msg}")
                return False, msg

        except Exception as e:
            logger.error(f"🚨 라이선스 검증 중 예외 발생: {e}")
            return False, f"서버 통신 오류: {str(e)}"

    @classmethod
    def is_trial_available(cls) -> bool:
        """[REST 경량화] 서버(Supabase) 및 로컬 DB를 모두 체크하여 체험판 가능 여부를 판단합니다."""
        hwid = cls.get_hwid()
        
        # 1. 서버(Supabase) REST API 직접 조회 (0.5초 타임아웃 강제화)
        try:
            url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/trial_logs?hwid=eq.{hwid}&select=used_count,created_at"
            headers = {
                "apikey": config.SUPABASE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            res = requests.get(url, headers=headers, timeout=0.5)
            if res.status_code == 200:
                data = res.json()
                if data:
                    used_count = data[0].get("used_count", 0)
                    created_at_str = data[0].get("created_at")
                    
                    if used_count >= 50:
                        logger.warning(f"🚫 서버 기록: HWID {hwid} 체험판 한도 소진 (50건)")
                        return False
        except requests.exceptions.Timeout:
            logger.warning("⚠️ 서버 체험판 조회 시간 초과 (0.5초 제한) - 로컬 검증 진행")
        except Exception as e:
            logger.error(f"서버 체험판 조회 실패: {e}")

        # 2. 로컬 DB 체크 (누적 수집량)
        try:
            db = LocalDBHandler()
            count = db.get_count()
            return count < 50
        except Exception as e:
            logger.error(f"Local trial availability check error: {e}")
            return False

    @classmethod
    def get_and_sync_trial_used_count(cls) -> int:
        """Supabase와 AppData 설정을 비교하여 더 큰 값으로 체험판 누적 사용량을 동기화합니다."""
        if cls._serial_key != "TRIAL-MODE":
            return 0
            
        try:
            hwid = cls.get_hwid()
            
            # 1. AppData에서 로컬 카운트 읽기
            import json
            appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "MarketingMonster", config.PRODUCT_ID)
            settings_file = os.path.join(appdata_dir, "trial_settings.json")
            
            local_count = 0
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        local_count = data.get("used_count", 0)
                except: pass
                
            # 2. Supabase에서 서버 카운트 읽기
            url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/trial_logs?hwid=eq.{hwid}&select=used_count"
            headers = {
                "apikey": config.SUPABASE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            res = requests.get(url, headers=headers, timeout=2.0)
            server_count = 0
            if res.status_code == 200:
                data = res.json()
                if data:
                    server_count = data[0].get("used_count", 0)
                else:
                    # 서버에 기록이 없다면 (어드민이 삭제/초기화 한 경우) 로컬 기록도 강제 초기화
                    local_count = 0
                
            # 3. 최대값을 진실로 채택 (서버가 0이면 로컬도 0이므로 초기화됨)
            true_count = max(local_count, server_count)
            
            # 4. AppData 및 Supabase에 업데이트
            cls.update_trial_used_count(true_count)
            
            cls._trial_baseline = true_count
            cls._trial_session_max = 0
            return true_count
        except Exception as e:
            logger.error(f"체험판 수집량 동기화 실패: {e}")
            return cls._trial_baseline

    @classmethod
    def update_trial_used_count(cls, new_count: int):
        """새로운 체험판 수집량을 AppData와 Supabase에 반영합니다."""
        try:
            hwid = cls.get_hwid()
            
            # AppData 업데이트
            import json
            appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "MarketingMonster", config.PRODUCT_ID)
            os.makedirs(appdata_dir, exist_ok=True)
            settings_file = os.path.join(appdata_dir, "trial_settings.json")
            
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump({"used_count": new_count}, f)
                
            # Supabase 업데이트 (Upsert로 변경하여 최초 누락 시에도 강제 등록)
            update_url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/trial_logs"
            payload = {
                "hwid": hwid,
                "status": "active",
                "used_count": new_count
            }
            headers = {
                "apikey": config.SUPABASE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates"
            }
            requests.post(update_url, headers=headers, json=payload, timeout=2.0)
        except Exception as e:
            logger.error(f"체험판 수집량 업데이트 실패: {e}")
            
    @classmethod
    def record_session_progress(cls, session_saved: int):
        """현재 크롤링 세션에서 수집된 양을 실시간으로 반영합니다."""
        if cls._serial_key != "TRIAL-MODE":
            return
            
        with cls._trial_lock:
            if session_saved > cls._trial_session_max:
                increment = session_saved - cls._trial_session_max
                cls._trial_session_max = session_saved
                cls._trial_baseline += increment
                new_baseline = cls._trial_baseline
            else:
                return
                
        # Do network call outside lock
        cls.update_trial_used_count(new_baseline)

    @classmethod
    def start_trial(cls) -> tuple[bool, str]:
        """[REST 경량화] 키 없이 즉시 체험판 모드로 시작합니다. (생애 1회 50건)"""
        try:
            # [NEW] 한도가 끝나도 대시보드 내부 진입은 허용 (크롤링 시작 시에만 차단)

            # 서버에 체험판 시작 기록 (Supabase REST API Upsert 직접 통신)
            hwid = cls.get_hwid()
            try:
                url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/trial_logs"
                headers = {
                    "apikey": config.SUPABASE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"
                }
                payload = {
                    "hwid": hwid,
                    "status": "active"
                }
                requests.post(url, headers=headers, json=payload, timeout=2.0)
            except Exception as e:
                logger.error(f"서버 체험판 기록 실패: {e}")

            cls._serial_key = "TRIAL-MODE"
            cls._collection_limit = 50 # 체험판은 총 50건으로 제한 (생애 1회)
            logger.info("⚡ 체험판 모드로 진입합니다. (생애 1회 한정: 50건)")
            return True, "체험판 모드로 시작합니다."
        except Exception as e:
            logger.error(f"체험판 시작 오류: {e}")
            return False, str(e)

    @classmethod
    def save_local_license(cls, key: str):
        """로컬 파일 서명 보존 방식 유지"""
        hwid = cls.get_hwid()
        signature = hashlib.sha256(f"{key}-{hwid}-CAFE-MONSTER".encode()).hexdigest()
        os.makedirs(os.path.dirname(cls.LICENSE_FILE), exist_ok=True)
        with open(cls.LICENSE_FILE, "w", encoding="utf-8-sig") as f:
            f.write(f"{key}:{signature}")

    @classmethod
    def check_license_status(cls) -> bool:
        # [NEW] Environment-based Trial Mode Detection (for cross-process sync)
        if os.environ.get("NPLACE_TRIAL_MODE") == "1":
            cls._serial_key = "TRIAL-MODE"
            cls._collection_limit = 50
            return True

        # [NEW] Trial Mode Bypass (Monster Rule 1.3)
        if cls._serial_key == "TRIAL-MODE":
            return True
            
        if not os.path.exists(cls.LICENSE_FILE): return False
        try:
            with open(cls.LICENSE_FILE, "r", encoding="utf-8-sig") as f:
                content = f.read().strip()
                if ":" not in content: return False
                key, stored_sig = content.split(":")
            hwid = cls.get_hwid()
            if stored_sig != hashlib.sha256(f"{key}-{hwid}-CAFE-MONSTER".encode()).hexdigest():
                return False
            success, _ = cls.validate_and_bind_key(key)
            return success
        except: return False

    @classmethod
    def create_license(cls, prefix: str = "CM", days: int = 30, collection_limit: int = None) -> tuple[bool, str]:
        """[REST 경량화] 수파베이스 DB에 새로운 라이선스 키를 생성하고 등록합니다. (Monster 전용)"""
        import secrets
        import string
        from datetime import timedelta

        # 1. 랜덤 시리얼 키 생성 (CM-PRO-XXXX-XXXX 형식)
        suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        serial_key = f"{prefix}-{suffix[:4]}-{suffix[4:]}"
        
        expire_date = (datetime.utcnow() + timedelta(days=days)).isoformat()

        try:
            url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/licenses"
            headers = {
                "apikey": config.SUPABASE_KEY,
                "Authorization": f"Bearer {config.SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            data = {
                "serial_key": serial_key,
                "status": "unused",
                "expire_date": expire_date,
                "collection_limit": collection_limit,
                "created_at": datetime.utcnow().isoformat(),
                "product_id": config.PRODUCT_ID
            }
            res = requests.post(url, headers=headers, json=data, timeout=0.5)
            if res.status_code in [200, 201]:
                logger.info(f"✨ 새 라이선스 발행 성공: {serial_key}")
                return True, serial_key
            return False, f"DB 삽입 실패: {res.text}"
        except Exception as e:
            logger.error(f"라이선스 생성 중 오류: {e}")
            return False, str(e)

    @classmethod
    def get_collection_limit(cls): return cls._collection_limit
    @classmethod
    def get_serial_key(cls): return cls._serial_key
