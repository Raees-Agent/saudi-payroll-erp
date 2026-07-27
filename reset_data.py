#!/usr/bin/env python3
"""
Reset and wipe all sample/mock data from SQLite database for a fresh clean state.
"""
import sqlite3

DB_PATH = 'payroll_db.db'

def reset_all_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("============================================================")
    print("WIPING ALL EXISTING TEST / SAMPLE DATA")
    print("============================================================")
    
    tables_to_clear = [
        "invoice_items",
        "invoices",
        "customers",
        "catalog_items",
        "payrolls",
        "payroll_records",
        "attendance",
        "employees"
    ]
    
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            print(f"[CLEARED] Wiped all data from table: {table}")
        except Exception as e:
            print(f"[WARN] Error clearing {table}: {e}")
            
    conn.commit()
    conn.close()
    print("\n[OK] All existing sample data wiped successfully! Database is clean.")

if __name__ == "__main__":
    reset_all_data()
