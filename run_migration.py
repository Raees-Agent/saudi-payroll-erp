#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Script for Payroll Tracking Table
Adds new columns: govt_fee, tax_rate, service_type, file_url to tracking table
"""

import sqlite3
import sys
import os

# Set up UTF-8 encoding for Windows compatibility
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Database path relative to script location or workspace
DB_PATH = "payroll_db.db"

def run_migration():
    """Execute database schema migration."""
    print("=" * 60)
    print("PAYROLL DATABASE MIGRATION")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Always fetch current table structure first (PRAGMA doesn't support WHERE)
        cursor.execute("PRAGMA table_info(tracking)")
        updated_columns = cursor.fetchall()
        col_names = {col[1]: col[2] for col in updated_columns}
        print(f"\n[INFO] Current Tracking Table Structure:")
        print(f"      Column Names: {list(col_names.keys())}")
        
        # Define new columns to add
        new_columns = {
            'govt_fee': ('REAL', True),    # Allow NULL initially
            'tax_rate': ('REAL', True),     # Allow NULL initially  
            'service_type': ('TEXT', False), # Don't allow NULL
            'file_url': ('TEXT', True)      # Allow NULL (optional file upload)
        }
        
        print("\n[INFO] Columns to be added:")
        for col, info in new_columns.items():
            print(f"      - {col}: {info[0]}")
        
        # Add each column if not exists
        migration_sql = ""
        
        for col_name, (col_type, nullable) in new_columns.items():
            placeholder = 'NULL' if nullable else 'NOT NULL'
            sql = f"ALTER TABLE tracking ADD COLUMN {col_name} {col_type}"
            
            # Check if column exists by filtering results from PRAGMA
            cursor.execute("PRAGMA table_info(tracking)")
            all_columns = cursor.fetchall()
            existing_col_names = [col[1] for col in all_columns]
            
            if col_name not in existing_col_names:
                print(f"\n[INFO] Adding column: {col_name}")
                cursor.execute(sql)
                migration_sql += sql + "; "
        
        # Verify final schema
        cursor.execute("PRAGMA table_info(tracking)")
        final_columns = cursor.fetchall()
        final_col_names = {col[1]: col[2] for col in final_columns}
        
        print(f"\n[SUCCESS] Final Tracking Table Structure:")
        for col_name, col_type in final_col_names.items():
            print(f"  - {col_name:15}: {col_type}")
        
        if migration_sql:
            conn.commit()
            print("\n" + "=" * 60)
            print("[SUCCESS] MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
        else:
            print("\n[WARNING] All required columns already exist in tracking table.")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"\n[ERROR] Database Error: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] Migration Error: {e}")
        raise
    
    print("\n[NEXT STEPS]")
    print("   1. Run: python app.py")
    print("   2. Add new payroll records via /add_payroll endpoint")
    print("   3. View PDF invoices via /payroll/track/<emp_id>/<month>/<invoice_id>/download")

if __name__ == "__main__":
    run_migration()