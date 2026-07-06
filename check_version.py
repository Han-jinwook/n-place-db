import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(r"D:\N-Place-DB")
import config

res = requests.get(
    f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/app_versions?product_id=eq.NPlace-DB&order=version.desc&limit=1",
    headers={"apikey": config.SUPABASE_KEY, "Authorization": f"Bearer {config.SUPABASE_KEY}"}
)
print(res.json()[0]['version'])
