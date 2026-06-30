import os
import sys
import shutil
import requests
from dotenv import load_dotenv
from supabase import create_client
import config

def main():
    print("3. Assembling spoofed folders in temp_dist")
    temp_dir = "temp_dist"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    # PRO is already renamed in dist
    print("Copying PRO...")
    shutil.copytree("dist/NPlace-DB-PRO-v1.1.72", os.path.join(temp_dir, "NPlace-DB-PRO-v1.1.72"))
    
    # TRIAL needs to be copied from 1.1.74
    print("Copying TRIAL...")
    shutil.copytree("dist/NPlace-DB-TRIAL-v1.1.74", os.path.join(temp_dir, "NPlace-DB-TRIAL-v1.1.72"))
    old_exe = os.path.join(temp_dir, "NPlace-DB-TRIAL-v1.1.72", "NPlace-DB-TRIAL-v1.1.74.exe")
    new_exe = os.path.join(temp_dir, "NPlace-DB-TRIAL-v1.1.72", "NPlace-DB-TRIAL-v1.1.72.exe")
    if os.path.exists(old_exe):
        os.rename(old_exe, new_exe)

    print("4. Deploying to GitHub and Supabase")
    def zip_and_upload(dist_folder_name, zip_filename, github_pat, upload_url, headers):
        zip_filepath = os.path.join("dist", zip_filename)
        if os.path.exists(zip_filepath):
            try:
                os.remove(zip_filepath)
            except Exception:
                pass
        print(f"Zipping {dist_folder_name} to {zip_filename}...")
        shutil.make_archive(
            base_name=os.path.join("dist", zip_filename.replace(".zip", "")),
            format='zip',
            root_dir=temp_dir,
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

    # If release exists, find it, otherwise create it
    res = requests.post(f"https://api.github.com/repos/{github_repo}/releases", json={
        "tag_name": tag_name,
        "name": f"Release {tag_name}",
        "body": "Fix OTA update loop by tricking v1.1.72 updater"
    }, headers=headers)
    
    if res.status_code == 201:
        upload_url = res.json()["upload_url"].split("{")[0]
    else:
        res_get = requests.get(f"https://api.github.com/repos/{github_repo}/releases/tags/{tag_name}", headers=headers)
        release_data = res_get.json()
        upload_url = release_data["upload_url"].split("{")[0]
        for asset in release_data.get("assets", []):
            print(f"Deleting old asset {asset['name']}")
            requests.delete(asset["url"], headers=headers)

    zip_and_upload("NPlace-DB-PRO-v1.1.72", "NPlace-DB-Pro.zip", github_pat, upload_url, headers)
    zip_and_upload("NPlace-DB-TRIAL-v1.1.72", "NPlace-DB-Trial.zip", github_pat, upload_url, headers)

    supabase = create_client(config.SUPABASE_URL, service_key)
    github_download_url = f"https://github.com/{github_repo}/releases/download/{tag_name}/NPlace-DB-Pro.zip"
    
    print("Updating Supabase app_versions...")
    supabase.table("app_versions").upsert({
        "product_id": config.PRODUCT_ID,
        "version": "1.1.74",
        "download_url": github_download_url,
        "release_notes": "🛠️ 72버전 무한 업데이트 루프 픽스 완료 (v1.1.74 엔진 탑재)"
    }).execute()
    print("All done! Version 1.1.74 deployed successfully with spoofed 1.1.72 folders.")

if __name__ == "__main__":
    main()
