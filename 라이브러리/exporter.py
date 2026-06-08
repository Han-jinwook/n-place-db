# 🔱 Monster 공통 라이브러리 - exporter.py
# - 버전: v1.2
# - 갱신 일시: 2026-06-08
# - 관리 주체: Monster 총괄 AI (Hub AI)
#
# [파일명 명명 전략 - v1.2 개정]
# ┌─────────────────────────────────────────────────────────┐
# │  우선순위  │ 설명                         │ 예시          │
# ├────────────┼──────────────────────────────┼──────────────│
# │  1. 커스텀 │ 호출부에서 직접 전달한 키워드 │ 설렁탕집      │
# │  2. 기본값 │ 앱 고유 default_prefix 정의  │ N플레이스     │
# │  3. 폴백   │ 위 두 경우 모두 없을 때      │ Monster_export│
# └─────────────────────────────────────────────────────────┘
# 각 개별 앱은 MonsterExporter를 상속하거나 default_prefix를
# 인자로 넘겨 앱 고유 기본 키워드를 사전에 지정합니다.
# 사용자가 입력한 검색 키워드(설렁탕집 등)는 커스텀으로 넘깁니다.

import os
import sys
import datetime
import subprocess

class MonsterExporter:
    """
    [3Monster Master Library] 공통 데이터 내보내기 및 다운로드 경로 표준화 헬퍼 모듈
    모든 데이터의 저장 위치를 사용자 다운로드 폴더로 일원화하고,
    중복 저장을 예방하기 위한 MMDD_HHMM 단축형 타임스탬프 파일명 생성을 지원합니다.

    [v1.2] 파일명 prefix 3단계 전략 지원:
      1. custom_prefix  : 호출부에서 사용자 입력 키워드 등을 직접 전달 (최우선)
      2. default_prefix : 앱별 고정 기본 키워드 (2순위)
      3. fallback       : 'Monster_export' (최후 수단)
    """

    # ── 앱별 기본 prefix 등록 테이블 ─────────────────────────────
    # 새 앱 추가 시 Hub AI와 협의 후 아래 테이블에 등록합니다.
    # key: product_id (소문자 권장), value: 기본 파일명 prefix
    APP_DEFAULT_PREFIX = {
        "nplace-db":     "N플레이스",
        "cafecrawler":   "카페크롤러",
        "autocommenter": "자동댓글",
        # 신규 앱 추가 시 Hub AI와 상의 후 여기에 등록
    }

    @staticmethod
    def get_download_path():
        """사용자 OS에 최적화된 다운로드(Downloads) 폴더 경로를 반환합니다."""
        if sys.platform == "win32":
            user_profile = os.environ.get("USERPROFILE")
            if user_profile:
                download_dir = os.path.join(user_profile, "Downloads")
                if os.path.exists(download_dir):
                    return download_dir

        # macOS 및 Linux, 또는 fallback 처리
        return os.path.join(os.path.expanduser('~'), 'Downloads')

    @classmethod
    def generate_filename(cls, prefix, extension="xlsx"):
        """
        [강령 준수] 표준 파일명 생성기
        - 포맷: [키워드]_[MMDD_HHMM].[확장자]
        - 예: 설렁탕집_0608_1459.xlsx  /  N플레이스_0608_1459.csv

        prefix 우선순위:
          1. 인자로 전달된 prefix (None이 아닌 경우 최우선)
          2. 빈 문자열이면 'Monster_export' fallback 적용
        """
        timestamp = datetime.datetime.now().strftime("%m%d_%H%M")

        # 빈값 fallback
        safe_prefix = (prefix or "Monster_export").strip()

        # 파일명에 사용할 수 없는 특수문자 제거
        for char in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
            safe_prefix = safe_prefix.replace(char, '_')

        # 확장자 앞자리 점(.) 제거 대응
        clean_ext = extension.lstrip('.')

        return f"{safe_prefix}_{timestamp}.{clean_ext}"

    @classmethod
    def get_export_filepath(cls, custom_prefix=None, extension="xlsx",
                            product_id=None, default_prefix=None):
        """
        일원화된 다운로드 폴더 내의 최종 파일 저장 경로(절대경로)를 생성합니다.

        Args:
            custom_prefix  : 사용자 입력 키워드 등 동적 prefix (최우선)
                             예) '설렁탕집', '강남헬스장'
            extension      : 파일 확장자 ('xlsx' 또는 'csv')
            product_id     : 앱 식별자. APP_DEFAULT_PREFIX 테이블에서 기본값 조회용
                             예) 'nplace-db', 'cafecrawler'
            default_prefix : 앱 고유 기본 prefix (product_id 테이블보다 명시적)
                             예) 'N플레이스'

        우선순위: custom_prefix > default_prefix > APP_DEFAULT_PREFIX[product_id] > fallback
        """
        # 1순위: 직접 전달된 커스텀 키워드
        prefix = (custom_prefix or "").strip()

        # 2순위: 호출부에서 지정한 default_prefix
        if not prefix:
            prefix = (default_prefix or "").strip()

        # 3순위: product_id로 테이블 조회
        if not prefix and product_id:
            prefix = cls.APP_DEFAULT_PREFIX.get(product_id.lower(), "")

        # 최종 fallback
        if not prefix:
            prefix = "Monster_export"

        download_dir = cls.get_download_path()
        filename = cls.generate_filename(prefix, extension)
        return os.path.join(download_dir, filename)

    @staticmethod
    def open_in_explorer(filepath):
        """
        저장이 완료된 후, 해당 파일이 위치한 다운로드 폴더를 열고
        해당 파일을 윈도우 탐색기 상에서 포커싱/하이라이트합니다.
        """
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return False

        try:
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{abs_path}"', shell=True)
                return True
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", abs_path])
                return True
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(abs_path)])
                return True
        except Exception:
            return False
