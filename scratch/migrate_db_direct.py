import mysql.connector
import sys
from decimal import Decimal
import datetime

remote_config = {
    'user': 'foliux',
    'password': 'Test@123',
    'host': '158.220.101.59',
    'database': 'FOLIUX'
}

local_config = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'database': 'foliux'
}

tables = [
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
    'core_hiddensignal'
]

def migrate():
    r_conn = mysql.connector.connect(**remote_config)
    l_conn = mysql.connector.connect(**local_config)
    r_cursor = r_conn.cursor(dictionary=True)
    l_cursor = l_conn.cursor()

    l_cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

    for table in tables:
        print(f"Migrating table: {table}")
        r_cursor.execute(f"SELECT * FROM `{table}`")
        rows = r_cursor.fetchall()
        if not rows:
            print(f"  Empty table, skipping.")
            continue
        
        l_cursor.execute(f"TRUNCATE TABLE `{table}`")
        
        columns = list(rows[0].keys())
        # Escape column names with backticks
        escaped_columns = [f"`{c}`" for c in columns]
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO `{table}` ({', '.join(escaped_columns)}) VALUES ({placeholders})"
        
        data = []
        for row in rows:
            data.append(tuple(row.values()))
        
        # Using executemany in batches to avoid large query errors
        batch_size = 500
        for i in range(0, len(data), batch_size):
            l_cursor.executemany(sql, data[i:i+batch_size])
        
        print(f"  Migrated {len(rows)} rows.")

    l_cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    l_conn.commit()
    r_conn.close()
    l_conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
