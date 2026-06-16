# 🔱 Monster 공통 라이브러리 - auth.py
# - 버전: v1.0
# - 갱신 일시: 2026-05-18
# - 관리 주체: Monster 총괄 AI (Hub AI)

import os
import sys
import subprocess
import hashlib
import uuid
import requests
from datetime import datetime, timedelta, timezone

class MonsterAuth:
    """
    [3Monster Master Library] 공통 라이선스 검증 및 HWID 바인딩 모듈
    Supabase REST API를 직접 호출하여 외부 의존성(Supabase 라이브러리)을 없애고 
    빌드 용량을 최소화하며 0.5초 타임아웃을 강제 적용합니다.
    """
    
    def __init__(self, product_id, license_key, supabase_url=None, supabase_key=None):
        self.product_id = product_id
        self.license_key = license_key.strip()
        
        # 인자로 전달받지 못한 경우 환경변수 또는 NPlace-DB 기본값에서 획득
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL") or "https://suwinftalfgybvrnzruz.supabase.co"
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1d2luZnRhbGZneWJ2cm56cnV6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzMDQ3OTEsImV4cCI6MjA5MTg4MDc5MX0.OJAE_djjwIxR1pDNVx45HprOcAtU8gZopGJx8hvJMt4"
        
        self.hwid = self._get_hwid()
        self.timeout = 0.5  # 0.5초 타임아웃 강제화 (Monster 강령 준수)

    def _get_hwid(self):
        """기기 고유 식별자(HWID)를 정밀 산출합니다."""
        try:
            if sys.platform == "win32":
                output = subprocess.check_output(
                    'wmic csproduct get uuid', 
                    shell=True, 
                    stderr=subprocess.DEVNULL
                ).decode().split('\n')[1].strip()
                if output and "UUID" not in output:
                    return hashlib.sha256(output.encode('utf-8')).hexdigest()
        except Exception:
            pass
        
        # fallback: MAC 주소 기반 해싱
        node = uuid.getnode()
        return hashlib.sha256(str(node).encode('utf-8')).hexdigest()

    def _get_headers(self):
        """Supabase REST API 통신용 표준 헤더를 구성합니다."""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def verify_license(self):
        """
        라이선스 키를 실시간으로 검증하고 HWID를 기기에 영구 바인딩합니다.
        (True/False, 결과 메시지, 남은 한도 수량) 형태로 반환합니다.
        """
        if not self.supabase_url or not self.supabase_key:
            return False, "Supabase 접속 정보가 설정되지 않았습니다.", 0

        url = f"{self.supabase_url.rstrip('/')}/rest/v1/licenses?serial_key=eq.{self.license_key}&select=*"
        
        try:
            # 0.5초 타임아웃 적용하여 동기식 멈춤 현상 차단
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return False, "유효하지 않은 라이선스 키입니다.", 0

            license_info = data[0]
            
            # 제품군 일치 확인
            if license_info.get("product_id") != self.product_id:
                return False, f"본 프로그램({self.product_id})용 라이선스가 아닙니다.", 0

            status = license_info.get("status", "unused")
            bound_value = license_info.get("bound_value")
            expire_date_str = license_info.get("expire_date")
            collection_limit = license_info.get("collection_limit", 0)

            # 1. 만료 시간 체크
            if expire_date_str:
                # ISO 시간 파싱 (파이썬 호환성 고려)
                try:
                    expire_date = datetime.fromisoformat(expire_date_str.replace('Z', '+00:00'))
                except ValueError:
                    expire_date = datetime.strptime(expire_date_str[:19], "%Y-%m-%dT%H:%M:%S")
                
                if expire_date < datetime.utcnow():
                    self._update_status("expired")
                    return False, "만료된 라이선스 키입니다. 기간 연장이 필요합니다.", 0

            # 2. 상태 차단 여부 체크
            if status == "blocked":
                return False, "사용 정지(Block)된 라이선스 키입니다. 고객센터에 문의하세요.", 0

            # 3. 기기 바인딩 검증 (HWID 검증)
            if bound_value:
                if bound_value != self.hwid:
                    return False, "이미 다른 PC에 등록된 라이선스 키입니다. (1PC 1Key 원칙)", 0
            else:
                # 바인딩되지 않은 키(unused)인 경우 현재 HWID를 강제 등록하고 활성화(active) 처리
                license_type = license_info.get("license_type", "")
                success = self._bind_device(license_type=license_type)
                if not success:
                    return False, "기기 바인딩 등록 중 오류가 발생했습니다.", 0

            return True, "정상 인증되었습니다.", collection_limit

        except requests.exceptions.Timeout:
            return False, "인증 서버 응답 초과 (0.5초 제한). 네트워크를 확인해주세요.", 0
        except Exception as e:
            return False, f"서버 통신 오류가 발생했습니다: {str(e)}", 0

    def _bind_device(self, license_type: str = ""):
        """현재 HWID를 Supabase에 영구 바인딩합니다. 첫 실행일 기준으로 만료일도 재계산합니다."""
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/licenses?serial_key=eq.{self.license_key}"

        # license_type 별 만료 기간 (일 단위)
        DURATION_MAP = {
            "TRIAL":    5,
            "1M":       30,
            "3M":       90,
            "6M":       180,
            "LIFETIME": None,  # None = 만료 없음
        }
        now_utc = datetime.now(timezone.utc)
        days = DURATION_MAP.get(license_type)
        new_expire = (now_utc + timedelta(days=days)).isoformat() if days is not None else None

        payload = {
            "bound_value": self.hwid,
            "status": "active",
            "first_run_date": now_utc.isoformat(),
        }
        if new_expire is not None:
            payload["expire_date"] = new_expire

        try:
            res = requests.patch(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            return res.status_code in [200, 201, 204]
        except Exception:
            return False

    def _update_status(self, new_status):
        """라이선스 상태 값을 원격으로 변경합니다."""
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/licenses?serial_key=eq.{self.license_key}"
        payload = {"status": new_status}
        try:
            requests.patch(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
        except Exception:
            pass
