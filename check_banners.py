import os
from supabase import create_client
import config

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
res = supabase.table('promotions').select('*').execute()
for p in res.data:
    print(f"ID: {p['id']}, image_url: {p.get('image_url')}")
