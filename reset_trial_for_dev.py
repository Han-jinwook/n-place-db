import os
import json
import requests
import hashlib
import subprocess

import config

def get_hwid():
    """간단하게 현재 PC의 HWID를 가져옵니다 (기존과 동일한 방식)"""
    try:
        output = subprocess.check_output('wmic csproduct get uuid', shell=True).decode().split('\n')[1].strip()
        if output:
            return hashlib.sha256(output.encode()).hexdigest()
    except:
        pass
    return "UNKNOWN-TEST-HWID"

def reset_trial():
    print("=== [개발자 모드] 체험판 초기화 도구 ===")
    
    # 1. AppData 초기화
    appdata_dir = os.path.join(os.environ.get("APPDATA", ""), "MarketingMonster", config.PRODUCT_ID)
    settings_file = os.path.join(appdata_dir, "trial_settings.json")
    if os.path.exists(settings_file):
        try:
            os.remove(settings_file)
            print("✅ 1. 로컬 설정 초기화 완료 (%APPDATA% 의 trial_settings.json 삭제)")
        except Exception as e:
            print(f"❌ 로컬 설정 삭제 실패: {e}")
    else:
        print("✅ 1. 로컬 설정 없음 (이미 초기화됨)")

    # 2. 로컬 DB 초기화 (선택적)
    db_file = os.path.join(os.path.expanduser("~"), "Documents", "MarketingMonster", "NPlace-DB", "NPlace-DB.sqlite")
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("✅ 2. 기존 수집된 로컬 DB 삭제 완료")
        except Exception as e:
            print(f"❌ 로컬 DB 삭제 실패: {e}")
            
    # 3. Supabase 서버 초기화
    hwid = get_hwid()
    try:
        url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/trial_logs?hwid=eq.{hwid}"
        headers = {
            "apikey": config.SUPABASE_KEY,
            "Authorization": f"Bearer {config.SUPABASE_KEY}",
        }
        res = requests.delete(url, headers=headers, timeout=5.0)
        if res.status_code in [200, 204]:
            print(f"✅ 3. 서버(Supabase) 초기화 완료 (HWID: {hwid} 데이터 삭제)")
        else:
            print(f"⚠️ 서버 초기화 응답 이상: {res.status_code}")
    except Exception as e:
        print(f"❌ 서버 초기화 실패: {e}")
        
    print("\n🎉 모든 초기화가 완료되었습니다. 이제 다시 체험판을 테스트할 수 있습니다!")
    input("종료하려면 엔터를 누르세요...")

if __name__ == "__main__":
    reset_trial()
