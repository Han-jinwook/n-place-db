import requests
import config

update_url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/trial_logs?on_conflict=hwid"
payload = {
    "hwid": "TEST-HWID-12345",
    "status": "active",
    "used_count": 37,
    "last_collected_at": "2026-07-02T06:21:02.876672+00:00"
}
headers = {
    "apikey": config.SUPABASE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}
response = requests.post(update_url, headers=headers, json=payload)
print(response.status_code)
print(response.text)
