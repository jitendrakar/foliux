import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

REMOTE_CONFIG = {
    'user': os.environ.get("DB_USER", "foliux"),
    'password': os.environ.get("DB_PASSWORD", "Test@123"),
    'host': os.environ.get("DB_HOST", "158.220.101.59"),
    'database': os.environ.get("DB_NAME", "FOLIUX"),
    'port': int(os.environ.get("DB_PORT", 3306))
}

LOCAL_CONFIG = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'database': 'foliux',
    'port': 3306
}

def sync_ipo():
    try:
        source_conn = mysql.connector.connect(**LOCAL_CONFIG)
        dest_conn = mysql.connector.connect(**REMOTE_CONFIG)
        
        source_cursor = source_conn.cursor(dictionary=True)
        dest_cursor = dest_conn.cursor()

        table = 'core_ipo'
        print(f"Syncing table: {table}...", flush=True)
        
        source_cursor.execute(f"SELECT * FROM `{table}`")
        rows = source_cursor.fetchall()
        
        if not rows:
            print("Local IPO table is empty. Nothing to push.")
            return

        dest_cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        dest_cursor.execute(f"TRUNCATE TABLE `{table}`")
        
        columns = list(rows[0].keys())
        escaped_columns = [f"`{c}`" for c in columns]
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO `{table}` ({', '.join(escaped_columns)}) VALUES ({placeholders})"
        
        data = [tuple(row.values()) for row in rows]
        dest_cursor.executemany(sql, data)
        
        dest_cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        dest_conn.commit()
        
        print(f"Successfully pushed {len(rows)} IPOs to VPS!", flush=True)
        
        source_conn.close()
        dest_conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    sync_ipo()
