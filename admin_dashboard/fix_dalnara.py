import sqlite3
db_path = r'C:\CafeMonster\NPlace-DB\data\NPlace-DB.sqlite'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("UPDATE shops SET instagram_handle = ? WHERE name = ?", 
            ('https://www.instagram.com/dalnara08/', '??[?€?œë‹˜ ?ŒìŠ¤??ê³„ì •]'))
conn.commit()
conn.close()
print('SUCCESS: Corrected test account URL to dalnara08')
