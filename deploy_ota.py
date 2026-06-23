import os
import sys
import shutil
import config
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

def main():
    print(f"[OTA Deployer] Starting OTA Deployment (GitHub + Supabase) for {config.PRODUCT_ID} v{config.CURRENT_VERSION}...")
    
    # Load environment variables from .env
    load_dotenv()
    
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    github_pat = os.getenv("GITHUB_PAT")
    
    if not service_key or not github_pat:
        print("[ERROR] Missing required keys in .env file.")
        print("Please ensure both SUPABASE_SERVICE_ROLE_KEY and GITHUB_PAT are set.")
        sys.exit(1)
        
    print("Keys loaded successfully.")
    
    # Verify dist folder exists
    dist_folder_name = f"{config.PRODUCT_ID}-v{config.CURRENT_VERSION}"
    dist_folder_path = os.path.join("dist", dist_folder_name)
    
    if not os.path.exists(dist_folder_path):
        print(f"[ERROR] Distribution folder not found: {dist_folder_path}")
        print("Please run build.bat first.")
        sys.exit(1)
        
    # Zip the dist folder
    zip_filename = f"{dist_folder_name}.zip"
    zip_filepath = os.path.join("dist", zip_filename)
    
    print(f"Compressing {dist_folder_path} to {zip_filepath}...")
    if os.path.exists(zip_filepath):
        os.remove(zip_filepath)
        
    shutil.make_archive(
        base_name=os.path.join("dist", dist_folder_name),
        format='zip',
        root_dir="dist",
        base_dir=dist_folder_name
    )
    print(f"Compression complete. File size: {os.path.getsize(zip_filepath) / (1024*1024):.2f} MB")
    
    # ---------------------------------------------------------
    # 1. GitHub Releases - Create Release & Upload Asset
    # ---------------------------------------------------------
    github_repo = "sundream7878/n-place-db"
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
        "body": f"Auto-generated release for {config.PRODUCT_ID} v{config.CURRENT_VERSION}",
        "draft": False,
        "prerelease": False,
        "generate_release_notes": False
    }
    
    res = requests.post(f"https://api.github.com/repos/{github_repo}/releases", json=release_payload, headers=headers)
    if res.status_code == 201:
        release_data = res.json()
        upload_url = release_data["upload_url"].split("{")[0]  # Remove {?name,label}
        print("GitHub Release created successfully.")
    elif res.status_code == 422: # Already exists, we need to fetch it
        print("Release tag already exists. Fetching existing release...")
        res_get = requests.get(f"https://api.github.com/repos/{github_repo}/releases/tags/{tag_name}", headers=headers)
        res_get.raise_for_status()
        release_data = res_get.json()
        upload_url = release_data["upload_url"].split("{")[0]
        
        # Check if asset already exists and delete it to overwrite
        for asset in release_data.get("assets", []):
            if asset["name"] == zip_filename:
                print(f"Deleting existing asset {zip_filename}...")
                requests.delete(asset["url"], headers=headers)
    else:
        print(f"[ERROR] Failed to create GitHub Release: {res.status_code} - {res.text}")
        sys.exit(1)
        
    print(f"Uploading {zip_filename} to GitHub Release...")
    with open(zip_filepath, "rb") as f:
        upload_headers = headers.copy()
        upload_headers["Content-Type"] = "application/zip"
        res_upload = requests.post(f"{upload_url}?name={zip_filename}", data=f, headers=upload_headers)
        res_upload.raise_for_status()
        
    asset_data = res_upload.json()
    public_url = asset_data["browser_download_url"]
    print(f"Upload complete. GitHub Download URL: {public_url}")
    
    # ---------------------------------------------------------
    # 2. Supabase - Update app_versions Table
    # ---------------------------------------------------------
    print("Registering version in Supabase app_versions table...")
    supabase: Client = create_client(config.SUPABASE_URL, service_key)
    
    existing = supabase.table("app_versions").select("*").eq("product_id", config.PRODUCT_ID).eq("version", config.CURRENT_VERSION).execute()
    
    if existing.data:
        supabase.table("app_versions").update({
            "download_url": public_url,
            "release_notes": f"Auto-deployed update for v{config.CURRENT_VERSION} (Hosted on GitHub)"
        }).eq("product_id", config.PRODUCT_ID).eq("version", config.CURRENT_VERSION).execute()
        print("Supabase DB record updated.")
    else:
        supabase.table("app_versions").insert({
            "product_id": config.PRODUCT_ID,
            "version": config.CURRENT_VERSION,
            "download_url": public_url,
            "release_notes": f"Auto-deployed release for v{config.CURRENT_VERSION} (Hosted on GitHub)"
        }).execute()
        print("Supabase DB record inserted.")
        
    print("OTA Deployment Pipeline finished successfully!")

if __name__ == "__main__":
    main()
