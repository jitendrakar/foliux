import mysql.connector
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
# Remote VPS Configuration (from settings.py / .env)
REMOTE_CONFIG = {
    'user': os.environ.get("DB_USER", "foliux"),
    'password': os.environ.get("DB_PASSWORD", "Test@123"),
    'host': os.environ.get("DB_HOST", "158.220.101.59"),
    'database': os.environ.get("DB_NAME", "FOLIUX"),
    'port': int(os.environ.get("DB_PORT", 3306))
}

# Local Configuration (from .env)
LOCAL_CONFIG = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'database': 'foliux',
    'port': 3306
}

# List of tables to synchronize
TABLES = [
    'django_content_type',
    'django_site',
    'auth_permission',
    'auth_group',
    'auth_user',
    'auth_user_groups',
    'auth_user_user_permissions',
    'account_emailaddress',
    'socialaccount_socialapp',
    'socialaccount_socialaccount',
    'socialaccount_socialtoken',
    'core_instrument',
    'core_profile',
    'core_portfolio',
    'core_transaction',
    'core_pnlstatement',
    'core_portfoliovaluehistory',
    'core_mutualfund',
    'core_mfportfolio',
    'core_mftransaction',
    'core_coin',
    'core_coinportfolio',
    'core_cointransaction',
    'core_npsfund',
    'core_npsportfolio',
    'core_npstransaction',
    'core_fixedasset',
    'core_otherasset',
    'core_loan',
    'core_loanpayment',
    'core_strategy',
    'core_strategystock',
    'core_watchlist',
    'core_hiddensignal',
    'core_userreview',
    'core_ipo',
    'core_chatbotknowledge',
    'core_dividend',
    'core_investmentgoal',
    'core_corporateaction',
    'core_signalnotificationstate',
    'core_familylink',
    'core_financialyeardata',
    'core_mfsip'
]

def sync_tables(source_config, dest_config):
    try:
        source_conn = mysql.connector.connect(**source_config)
        dest_conn = mysql.connector.connect(**dest_config)
        
        source_cursor = source_conn.cursor(dictionary=True)
        dest_cursor = dest_conn.cursor()

        # Disable foreign key checks for clean truncation and insertion
        dest_cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

        for table in TABLES:
            print(f"Syncing table: {table}...", flush=True)
            
            # Fetch data from source
            source_cursor.execute(f"SELECT * FROM `{table}`")
            rows = source_cursor.fetchall()
            
            if not rows:
                print(f"  Table {table} is empty. Truncating destination...", flush=True)
                dest_cursor.execute(f"TRUNCATE TABLE `{table}`")
                continue
            
            # Truncate destination
            dest_cursor.execute(f"TRUNCATE TABLE `{table}`")
            
            # Prepare insert statement
            columns = list(rows[0].keys())
            escaped_columns = [f"`{c}`" for c in columns]
            placeholders = ", ".join(["%s"] * len(columns))
            sql = f"INSERT INTO `{table}` ({', '.join(escaped_columns)}) VALUES ({placeholders})"
            
            # Batch insert data
            data = [tuple(row.values()) for row in rows]
            batch_size = 500
            for i in range(0, len(data), batch_size):
                dest_cursor.executemany(sql, data[i:i+batch_size])
            
            print(f"  Migrated {len(rows)} rows.", flush=True)

        dest_cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        dest_conn.commit()
        
        source_conn.close()
        dest_conn.close()
        print("\nDatabase synchronization complete!", flush=True)

    except mysql.connector.Error as err:
        print(f"Database error: {err}", flush=True)
    except Exception as e:
        print(f"Unexpected error: {e}", flush=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_database.py [pull | push]")
        print("  pull: VPS -> Local")
        print("  push: Local -> VPS")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode == "pull":
        print("PULLING data from VPS to Local...", flush=True)
        sync_tables(REMOTE_CONFIG, LOCAL_CONFIG)
    elif mode == "push":
        print("PUSHING data from Local to VPS...", flush=True)
        # WARNING: This overwrites the VPS data!
        confirm = input("WARNING: This will overwrite the VPS database with your local data. Proceed? (y/n): ")
        if confirm.lower() == 'y':
            sync_tables(LOCAL_CONFIG, REMOTE_CONFIG)
        else:
            print("❌ Sync cancelled.")
    else:
        print("Invalid mode. Use 'pull' or 'push'.")
