import pandas as pd
import sqlite3
import os
import config
from 라이브러리.exporter import MonsterExporter

def export_to_xlsx(db_path: str = None, prefix: str = "N플레이스"):
    """
    Exports all data from the SQLite 'shops' table to an Excel file.
    Returns the path to the created file, or None if failed.
    """
    if db_path is None:
        db_path = config.LOCAL_DB_PATH
        
    if not os.path.exists(db_path):
        return None

    try:
        # Connect and read
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM shops", conn)
        conn.close()

        if df.empty:
            return None

        # Use Standard downloads path and naming format
        file_path = MonsterExporter.get_export_filepath(prefix, "xlsx")

        # Drop internal columns if any
        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        # Save to Excel
        df.columns = [
            "상호명", "전화번호", "상세URL", "주소", "위도", "경도", 
            "이메일", "인스타그램", "네이버블로그", "톡톡URL", "대표자명", "검색키워드", "수집일시"
        ]
        
        df.to_excel(file_path, index=False, engine='openpyxl')
        
        # Auto-open in explorer
        MonsterExporter.open_in_explorer(file_path)
        
        return os.path.abspath(file_path)

    except Exception as e:
        print(f"Excel Export Error: {e}")
        return None

def export_to_csv(db_path: str = None, prefix: str = "N플레이스"):
    """
    Exports all data to a CSV file with utf-8-sig encoding for Excel compatibility.
    """
    if db_path is None:
        db_path = config.LOCAL_DB_PATH
        
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM shops", conn)
        conn.close()

        if df.empty:
            return None

        # Use Standard downloads path and naming format
        file_path = MonsterExporter.get_export_filepath(prefix, "csv")

        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        df.columns = [
            "상호명", "전화번호", "상세URL", "주소", "위도", "경도", 
            "이메일", "인스타그램", "네이버블로그", "톡톡URL", "대표자명", "검색키워드", "수집일시"
        ]
        
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        # Auto-open in explorer
        MonsterExporter.open_in_explorer(file_path)
        
        return os.path.abspath(file_path)

    except Exception as e:
        print(f"CSV Export Error: {e}")
        return None

if __name__ == "__main__":
    path = export_to_xlsx()
    if path:
        print(f"Export successful: {path}")
    else:
        print("Export failed.")
