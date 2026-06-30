import PyInstaller.__main__
import os
import shutil
import config
import re

def build_version(v, build_type):
    print(f"\n=========================================")
    print(f"N-Place-DB Build Start (v{v} - {build_type})")
    print(f"=========================================\n")

    # PyInstaller Arguments
    exe_name = f"NPlace-DB-{build_type}"
    args = [
        'NPlace_DB_Launcher.py',              
        f'--name={exe_name}',
        '--icon=assets/icon.ico',
        '--onedir',             
        '--noconsole',          
        '--noconfirm',          
        '--collect-all=streamlit',
        '--collect-all=pycryptodome',
        '--collect-all=customtkinter',
        '--collect-all=numpy',
        '--collect-all=pandas',
        '--add-data=admin_dashboard;admin_dashboard',
        '--add-data=messenger;messenger',
        '--add-data=crawler;crawler',
        '--add-data=assets;assets',
        '--add-data=config.py;.',
        '--add-data=admin_dashboard/templates.json;.',
        '--add-data=step1_refined_crawler.py;.',
        '--add-data=engine_recover_missing.py;.',
        '--add-data=auth.py;.',
        '--add-data=auth_gui.py;.',
        '--add-data=sb_auth_manager.py;.',
        '--add-data=updater.py;.',
        '--add-data=exporter.py;.',
        '--add-data=main_launcher.py;.',
        '--add-data=라이브러리;라이브러리',
        '--collect-all=playwright_stealth',
        '--collect-all=streamlit_autorefresh',
        '--hidden-import=step1_refined_crawler',
        '--hidden-import=engine_recover_missing',
        '--hidden-import=streamlit.runtime.scriptrunner.magic_funcs',
        '--hidden-import=email.mime.text',
        '--hidden-import=email.mime.multipart',
        '--hidden-import=email.mime.application',
        '--hidden-import=pandas._libs.tslibs.timedeltas',
        '--hidden-import=pandas._libs.tslibs.np_datetime',
        '--hidden-import=pandas._libs.tslibs.nattype',
        '--hidden-import=numpy.core._multiarray_umath',
        '--clean'
    ]
    
    # Execute Build
    try:
        PyInstaller.__main__.run(args)
        print(f"\n[{build_type} Build] PyInstaller compilation completed successfully!")
    except Exception as e:
        print(f"\n[{build_type} Build] Failed: {e}")

def modify_config_build_type(config_path, build_type):
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace BUILD_TYPE = "..." with the new build_type
    new_content = re.sub(r'BUILD_TYPE\s*=\s*"[^"]+"', f'BUILD_TYPE = "{build_type}"', content)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Modified config.py to BUILD_TYPE = '{build_type}'")

def build_all():
    v = config.CURRENT_VERSION
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
    
    # Save original config
    with open(config_path, 'r', encoding='utf-8') as f:
        original_config = f.read()

    try:
        # 1. Resilient Cleanup
        if os.path.exists("build"): shutil.rmtree("build", ignore_errors=True)
        print("Cleanup done (including pycache).")

        # 2. Build PRO version
        modify_config_build_type(config_path, "PRO")
        build_version(v, "PRO")
        
        # 3. Build TRIAL version
        modify_config_build_type(config_path, "TRIAL")
        build_version(v, "TRIAL")

    finally:
        # Restore original config.py
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(original_config)
        print("\nRestored original config.py")

if __name__ == "__main__":
    build_all()
