import os
import sys
import shutil
import config
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

def zip_and_upload(dist_folder_name, zip_filename, github_pat, upload_url, headers):
    dist_folder_path = os.path.join("dist", dist_folder_name)
    if not os.path.exists(dist_folder_path):
        print(f"[ERROR] Distribution folder not found: {dist_folder_path}")
        return False

    zip_filepath = os.path.join("dist", zip_filename)
    print(f"Compressing {dist_folder_path} to {zip_filepath}...")
    if os.path.exists(zip_filepath):
        os.remove(zip_filepath)
        
    shutil.make_archive(
        base_name=os.path.join("dist", zip_filename.replace(".zip", "")),
        format='zip',
        root_dir="dist",
        base_dir=dist_folder_name
    )
    print(f"Compression complete. File size: {os.path.getsize(zip_filepath) / (1024*1024):.2f} MB")

    print(f"Uploading {zip_filename} to GitHub Release...")
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = "application/zip"
    
    import time
    for attempt in range(3):
        try:
            with open(zip_filepath, "rb") as f:
                res_upload = requests.post(f"{upload_url}?name={zip_filename}", data=f, headers=upload_headers, timeout=120.0)
                res_upload.raise_for_status()
            print(f"Upload complete for {zip_filename}")
            return True
        except Exception as e:
            print(f"Upload attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return False

def main():
    print(f"[OTA Deployer] Starting DUAL OTA Deployment (GitHub + Supabase) for {config.PRODUCT_ID} v{config.CURRENT_VERSION}...")
    
    # Load environment variables from .env
    load_dotenv()
    
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    github_pat = os.getenv("GITHUB_PAT")
    
    if not service_key or not github_pat:
        print("[ERROR] Missing required keys in .env file.")
        print("Please ensure both SUPABASE_SERVICE_ROLE_KEY and GITHUB_PAT are set.")
        sys.exit(1)
        
    print("Keys loaded successfully.")
    
    # ---------------------------------------------------------
    # 1. GitHub Releases - Create Release
    # ---------------------------------------------------------
    github_repo = "Han-jinwook/n-place-db"
    tag_name = f"v{config.CURRENT_VERSION}"
    print(f"Creating GitHub Release {tag_name} in {github_repo}...")
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_pat}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # Create Release
    release_payload = {
        "tag_name": tag_name,
        "target_commitish": "main",
        "name": f"Release {tag_name}",
        "body": f"Auto-generated release for {config.PRODUCT_ID} v{config.CURRENT_VERSION} (Dual Build)",
        "draft": False,
        "prerelease": False,
        "generate_release_notes": False
    }
    
    res = requests.post(f"https://api.github.com/repos/{github_repo}/releases", json=release_payload, headers=headers)
    if res.status_code == 201:
        release_data = res.json()
        upload_url = release_data["upload_url"].split("{")[0]
        print("GitHub Release created successfully.")
    elif res.status_code == 422: # Already exists
        print("Release tag already exists. Fetching existing release...")
        res_get = requests.get(f"https://api.github.com/repos/{github_repo}/releases/tags/{tag_name}", headers=headers)
        res_get.raise_for_status()
        release_data = res_get.json()
        upload_url = release_data["upload_url"].split("{")[0]
        
        # Check if assets already exist and delete them to overwrite
        for asset in release_data.get("assets", []):
            if "Map_DB" in asset["name"] or "NPlace-DB" in asset["name"]:
                print(f"Deleting existing asset {asset['name']}...")
                requests.delete(asset["url"], headers=headers)
    else:
        print(f"[ERROR] Failed to create GitHub Release: {res.status_code} - {res.text}")
        sys.exit(1)

    # Zip and Upload PRO
    zip_pro = f"Map_DB-Pro-v{config.CURRENT_VERSION}.zip"
    folder_pro = f"Map_DB-PRO"
    success_pro = zip_and_upload(folder_pro, zip_pro, github_pat, upload_url, headers)

    # Zip and Upload TRIAL
    zip_trial = f"Map_DB-Trial-v{config.CURRENT_VERSION}.zip"
    folder_trial = f"Map_DB-TRIAL"
    success_trial = zip_and_upload(folder_trial, zip_trial, github_pat, upload_url, headers)

    if not success_pro and not success_trial:
        print("[ERROR] Failed to find distribution folders. Did you run build_exe.py?")
        sys.exit(1)

    # ---------------------------------------------------------
    # 2. Supabase - Update app_versions Table
    # ---------------------------------------------------------
    print("Registering version in Supabase app_versions table...")
    supabase: Client = create_client(config.SUPABASE_URL, service_key)
    
    # Base URL using the PRO version. updater.py will modify this if it's a TRIAL build
    github_download_url = f"https://github.com/{github_repo}/releases/download/{tag_name}/{zip_pro}"
    
    for p_id in [config.PRODUCT_ID, "NPlace-DB"]:
        supabase.table("app_versions").upsert({
            "product_id": p_id,
            "version": config.CURRENT_VERSION,
            "download_url": github_download_url,
            "release_notes": f"⚡ {config.SERVICE_NAME_KR} Map_DB Pro 업그레이드 및 기능 개선 (v{config.CURRENT_VERSION})"
        }).execute()
    
    print("Supabase DB records inserted.")
    print("OTA Deployment Pipeline finished successfully!")

if __name__ == "__main__":
    main()
