import PyInstaller.__main__
import os
import shutil
import config
import re

def build_version(v, build_type, pyarmor_runtime):
    print(f"\n=========================================")
    print(f"N-Place-DB Build Start (v{v} - {build_type})")
    print(f"=========================================\n")

    # PyInstaller Arguments
    exe_name = f"Map_DB-{build_type}"
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
        '--add-data=engine_recover_missing.py;.',
        '--add-data=auth_gui.py;.',
        '--add-data=updater.py;.',
        '--add-data=exporter.py;.',
        '--add-data=main_launcher.py;.',
        '--add-data=라이브러리;라이브러리',
        f'--add-data=step1_refined_crawler.py;.',
        f'--add-data=auth.py;.',
        f'--add-data={pyarmor_runtime};{pyarmor_runtime}',
        f'--hidden-import={pyarmor_runtime}',
        '--collect-all=playwright_stealth',
        '--collect-all=streamlit_autorefresh',
        '--hidden-import=sb_auth_manager',
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
        
        # Rename the output folder from dist/Map_DB-{build_type} to dist/Map_DB-{build_type}-v{v}
        src_dir = os.path.join("dist", exe_name)
        dst_dir = os.path.join("dist", f"Map_DB-{build_type}-v{v}")
        print(f"Renaming compiled directory {src_dir} to {dst_dir}...")
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir, ignore_errors=True)
        if os.path.exists(src_dir):
            os.rename(src_dir, dst_dir)
            print(f"Successfully renamed output folder to: {dst_dir}")
        else:
            print(f"[Warning] Compiled directory not found: {src_dir}")
            
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

    target_scripts = ["step1_refined_crawler.py", "auth.py", "sb_auth_manager.py"]
    pyarmor_runtime = None

    try:
        # 1. Resilient Cleanup
        if os.path.exists("build"): shutil.rmtree("build", ignore_errors=True)
        for root_dir, dirs, _ in os.walk("."):
            for d in dirs:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(root_dir, d), ignore_errors=True)
        print("Cleanup done (including pycache).")

        # 2. Run PyArmor Obfuscation ONCE for both builds
        print("\n[Global] Running PyArmor Obfuscation...")
        if os.path.exists("obf_dist"):
            shutil.rmtree("obf_dist")
        
        os.system(f"pyarmor gen -O obf_dist {' '.join(target_scripts)}")
        
        for item in os.listdir("obf_dist"):
            if item.startswith("pyarmor_runtime_"):
                pyarmor_runtime = item
                break

        if not pyarmor_runtime:
            print("[Error] PyArmor runtime not found. PyArmor might not be installed or failed.")
            return

        print("[Global] Backing up original scripts and applying obfuscated scripts...")
        for script in target_scripts:
            if os.path.exists(script):
                shutil.copy2(script, script + ".bak")
                shutil.copy2(os.path.join("obf_dist", script), script)
                
        if os.path.exists(pyarmor_runtime):
            shutil.rmtree(pyarmor_runtime)
        shutil.copytree(os.path.join("obf_dist", pyarmor_runtime), pyarmor_runtime)

        # 3. Build PRO version
        modify_config_build_type(config_path, "PRO")
        build_version(v, "PRO", pyarmor_runtime)
        
        # 4. Build TRIAL version
        modify_config_build_type(config_path, "TRIAL")
        build_version(v, "TRIAL", pyarmor_runtime)

    finally:
        # Restore original config.py
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(original_config)
        
        # Restore original scripts
        print("[Global] Restoring original scripts...")
        for script in target_scripts:
            if os.path.exists(script + ".bak"):
                shutil.move(script + ".bak", script)
                
        # Clean up lingering pyarmor runtime and pycache from root to prevent script errors
        for item in os.listdir("."):
            if item.startswith("pyarmor_runtime_") and os.path.isdir(item):
                shutil.rmtree(item, ignore_errors=True)
        if os.path.exists("obf_dist"):
            shutil.rmtree("obf_dist", ignore_errors=True)
        for root_dir, dirs, _ in os.walk("."):
            for d in dirs:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(root_dir, d), ignore_errors=True)
                    
        print("\nRestored original config.py & cleaned temporary files.")

if __name__ == "__main__":
    build_all()
