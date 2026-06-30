import os
from supabase import create_client, Client
import config
from dotenv import load_dotenv

load_dotenv()

supabase_url: str = os.getenv("VITE_SUPABASE_URL")
supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

supabase.table('app_versions').update({
    "release_notes": "N-Place-DB 최신 버전이 출시되었습니다. (버그 수정 및 안정성 개선)"
}).eq("version", "1.1.71").execute()

print("Updated 1.1.71 release notes to Korean.")
