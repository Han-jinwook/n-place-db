# Map_DB 빌드 오류 현황 및 다음 세션 작업 가이드

## 1. 현재 발생한 오류
`Map_DB-TRIAL.exe` 또는 `PRO` 버전을 실행하면 다음과 같은 에러창이 팝업되며 실행이 중단됩니다.
```text
Failed to execute script 'NPlace_DB_Launcher' due to unhandled exception: No module named 'sb_auth_manager'
Traceback (most recent call last):
  File "NPlace_DB_Launcher.py", line 8, in <module>
  File "pyimod02_importers.py", line 457, in exec_module
  File "<frozen auth>", line 3, in <module>
ModuleNotFoundError: No module named 'sb_auth_manager'
```

## 2. 오류 발생의 근본 원인 (Root Cause)
이 문제는 **PyArmor(코드 난독화)와 PyInstaller(exe 패키징) 간의 동작 방식 차이** 때문에 발생했습니다.

1. `NPlace_DB_Launcher.py`는 `auth.py`를 임포트합니다.
2. `auth.py`는 내부에서 `sb_auth_manager.py`를 임포트하여 Supabase 인증을 처리합니다.
3. 하지만 빌드 스크립트(`build_exe.py`)가 실행될 때, `auth.py`를 먼저 PyArmor로 암호화(난독화)해버립니다.
4. 이후 PyInstaller가 exe로 패키징하기 위해 소스 코드들을 스캔하면서 어떤 모듈이 필요한지 추적하는데, **`auth.py`가 이미 난독화되어 외계어처럼 변해있으므로 그 안에 적혀있던 `import sb_auth_manager`라는 코드를 읽지 못합니다.**
5. 결국 PyInstaller는 `sb_auth_manager`가 필요하다는 사실을 모른 채 exe 패키징을 완료해버리고, 실행 시 모듈이 없다는 에러가 발생하게 됩니다.

*(이전의 1170 에러(런타임 불일치)는 원본 복구로 완벽히 해결되었지만, 원본이 정상적으로 암호화되면서 PyInstaller의 의존성 추적을 피하게 된 새로운 사이드 이펙트입니다.)*

## 3. 다음 세션에서의 해결 방안 (Action Plan)
해결 방법은 아주 간단하며 명확합니다. PyInstaller가 난독화된 코드 내부를 읽지 못하더라도 강제로 모듈을 포함시키도록 지시하면 됩니다.

**수정할 파일**: `build_exe.py`
**수정 내용**: PyInstaller 빌드 옵션(`args`)에 `--hidden-import`를 추가하여 누락된 모듈들을 명시적으로 포함시킵니다.

```python
        args = [
            'NPlace_DB_Launcher.py',
            '--name', f'Map_DB-{build_type}',
            '--windowed',
            '--noconfirm',
            '--clean',
            f'--icon={icon_path}',
            f'--add-data={pyarmor_runtime};{pyarmor_runtime}',
            f'--hidden-import={pyarmor_runtime}',
            
            # --- [다음 세션 추가할 내용] ---
            '--hidden-import=sb_auth_manager', # 난독화된 auth.py가 호출하는 모듈 강제 포함
            '--hidden-import=config',          # 혹시 모를 누락 방지용 설정 파일 포함
            # -------------------------------
        ]
```

## 4. 요약
* **상태**: 암호화 키 불일치 문제(1170 에러)는 100% 해결됨.
* **현재 문제**: 난독화 때문에 PyInstaller가 일부 모듈 패키징을 빠뜨림.
* **해결책**: `build_exe.py`에 `--hidden-import=sb_auth_manager` 한 줄만 추가하면 완벽하게 해결됨.

다음 세션에서 이 문서를 기반으로 1분 안에 수정을 완료하고 최종 빌드를 뽑아내겠습니다!
