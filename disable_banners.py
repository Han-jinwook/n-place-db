import os
from supabase import create_client
import config

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
res = supabase.table('promotions').select('*').execute()
for p in res.data:
    if p.get('promote_product_id') != config.PRODUCT_ID:
        print(f"Disabling promotion {p.get('id')}")
        supabase.table('promotions').update({'is_active': False}).eq('id', p.get('id')).execute()
    else:
        print(f"Enabling promotion {p.get('id')}")
        supabase.table('promotions').update({'is_active': True}).eq('id', p.get('id')).execute()
print("Done")
