import sys
import os

# Add obf_dist and project root to sys.path
sys.path.insert(0, os.path.abspath("obf_dist"))
sys.path.insert(0, os.path.abspath("."))

try:
    print("Trying to import auth from obf_dist...")
    from auth import AuthManager
    print("Success! AuthManager imported successfully.")
except Exception as e:
    print(f"Failed to import auth: {e}")
    import traceback
    traceback.print_exc()
