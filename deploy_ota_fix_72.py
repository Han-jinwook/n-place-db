import os
import sys
import shutil
import requests
import re
from dotenv import load_dotenv
from supabase import create_client

def main():
    print("1. Updating config.py to 1.1.74")
    config_path = "config.py"
    with open(config_path, "r", encoding="utf-8") as f:
        config_content = f.read()
        
    config_content = re.sub(r'CURRENT_VERSION\s*=\s*"[^"]+"', 'CURRENT_VERSION = "1.1.74"', config_content)
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    import config
    import importlib
    importlib.reload(config)

    print("2. Building 1.1.74 via build_exe.py")
    import build_exe
    build_exe.build_all()

    print("3. Renaming folders to spoof 1.1.72 for the old broken updater")
    for build_type in ["PRO", "TRIAL"]:
        old_folder = os.path.join("dist", f"NPlace-DB-{build_type}-v1.1.74")
        new_folder = os.path.join("dist", f"NPlace-DB-{build_type}-v1.1.72")
        
        if os.path.exists(new_folder):
            shutil.rmtree(new_folder)
            
        if not os.path.exists(old_folder):
            print(f"Error: {old_folder} does not exist!")
            sys.exit(1)
            
        os.rename(old_folder, new_folder)
        
        old_exe = os.path.join(new_folder, f"NPlace-DB-{build_type}-v1.1.74.exe")
        new_exe = os.path.join(new_folder, f"NPlace-DB-{build_type}-v1.1.72.exe")
        os.rename(old_exe, new_exe)
        print(f"Spoofed: {old_exe} -> {new_exe}")

    print("4. Deploying to GitHub and Supabase")
    def zip_and_upload(dist_folder_name, zip_filename, github_pat, upload_url, headers):
        zip_filepath = os.path.join("dist", zip_filename)
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)
        print(f"Zipping {dist_folder_name} to {zip_filename}...")
        shutil.make_archive(
            base_name=os.path.join("dist", zip_filename.replace(".zip", "")),
            format='zip',
            root_dir="dist",
            base_dir=dist_folder_name
        )
        print(f"Uploading {zip_filename}...")
        with open(zip_filepath, "rb") as f:
            upload_headers = headers.copy()
            upload_headers["Content-Type"] = "application/zip"
            res = requests.post(f"{upload_url}?name={zip_filename}", data=f, headers=upload_headers)
            res.raise_for_status()
        return True

    load_dotenv()
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    github_pat = os.getenv("GITHUB_PAT")
    github_repo = "Han-jinwook/n-place-db"
    tag_name = "v1.1.74"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_pat}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    release_payload = {
        "tag_name": tag_name,
        "target_commitish": "main",
        "name": f"Release {tag_name}",
        "body": "Fix OTA update loop by tricking v1.1.72 updater",
        "draft": False,
        "prerelease": False
    }
    
    res = requests.post(f"https://api.github.com/repos/{github_repo}/releases", json=release_payload, headers=headers)
    if res.status_code == 201:
        upload_url = res.json()["upload_url"].split("{")[0]
    elif res.status_code == 422:
        res_get = requests.get(f"https://api.github.com/repos/{github_repo}/releases/tags/{tag_name}", headers=headers)
        release_data = res_get.json()
        upload_url = release_data["upload_url"].split("{")[0]
        for asset in release_data.get("assets", []):
            print(f"Deleting old asset {asset['name']}")
            requests.delete(asset["url"], headers=headers)
    else:
        print(res.text)
        sys.exit(1)

    zip_and_upload("NPlace-DB-PRO-v1.1.72", "NPlace-DB-Pro.zip", github_pat, upload_url, headers)
    zip_and_upload("NPlace-DB-TRIAL-v1.1.72", "NPlace-DB-Trial.zip", github_pat, upload_url, headers)

    supabase = create_client(config.SUPABASE_URL, service_key)
    github_download_url = f"https://github.com/{github_repo}/releases/download/{tag_name}/NPlace-DB-Pro.zip"
    
    print("Updating Supabase app_versions...")
    supabase.table("app_versions").upsert({
        "product_id": config.PRODUCT_ID,
        "version": "1.1.74",
        "download_url": github_download_url,
        "release_notes": "🛠️ 72버전 무한 업데이트 버그 픽스 및 엔진 안정화 (v1.1.74)"
    }).execute()
    print("All done! Version 1.1.74 deployed successfully with spoofed 1.1.72 folders.")

if __name__ == "__main__":
    main()
