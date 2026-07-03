import os
from supabase import create_client
import config

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

# Disable the 3Monster banner
supabase.table('promotions').update({'is_active': False}).eq('id', 'cade82e8-0ff5-4412-83a5-85168c9ed48d').execute()

# Update the other banner to be NPlace-DB and enable it
supabase.table('promotions').update({
    'title': '🚀 NPlace-DB 압도적인 마케팅 DB 추출 솔루션!',
    'promote_product_id': 'NPlace-DB',
    'is_active': True,
    'url': 'https://3monster.netlify.app/'
}).eq('id', 'f3bfaffa-15f9-4e45-bfd8-598a4d3d0223').execute()

print("Banners updated!")
