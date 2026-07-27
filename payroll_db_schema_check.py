#!/usr/bin/env python3
"""Check and migrate payroll database schema for Saudi Enterprise HR & WPS compliance."""
import sqlite3

DB_PATH = 'payroll_db.db'

def check_and_migrate_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("SAUDI ENTERPRISE DATABASE SCHEMA MIGRATION")
    print("=" * 60)
    
    # 1. Create company_settings table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_settings (
        id INTEGER PRIMARY KEY,
        establishment_name TEXT DEFAULT 'Saudi Enterprise Corporation',
        cr_number TEXT DEFAULT '1010000000',
        qiwa_id TEXT DEFAULT 'QIW-998877',
        gosi_reg_number TEXT DEFAULT '998877665',
        vat_number TEXT DEFAULT '310000000000003',
        bank_code TEXT DEFAULT 'RIBL',
        company_iban TEXT DEFAULT 'SA0000000000000000000000',
        cr_expiry_date DATETIME NULL
    )
    """)
    conn.commit()

    # Migration for company_settings table
    comp_columns = {
        'company_iban': "TEXT DEFAULT 'SA0000000000000000000000'",
        'bank_code': "TEXT DEFAULT 'RIBL'",
        'vat_number': "TEXT DEFAULT '310000000000003'"
    }
    cursor.execute("PRAGMA table_info(company_settings)")
    existing_comp_cols = [col[1] for col in cursor.fetchall()]
    for col_name, col_def in comp_columns.items():
        if col_name not in existing_comp_cols:
            try:
                cursor.execute(f"ALTER TABLE company_settings ADD COLUMN {col_name} {col_def}")
                conn.commit()
            except Exception as e:
                pass
    
    # Insert default row in company_settings if empty
    cursor.execute("SELECT COUNT(*) FROM company_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO company_settings (id, establishment_name, cr_number, qiwa_id, gosi_reg_number, vat_number, bank_code, company_iban)
        VALUES (1, 'Saudi Enterprise Solutions Ltd', '1010889900', 'QIW-882211', '774411223', '310099887700003', 'RJHI', 'SA4480000000123456789012')
        """)
        conn.commit()
        print("[OK] Created default company_settings record")

    # 2. Migration for EMPLOYEES table
    emp_columns = {
        'nationality_type': "TEXT DEFAULT 'Expat'",
        'contract_type': "TEXT DEFAULT 'Indefinite'",
        'passport_number': "TEXT DEFAULT NULL",
        'joining_date': "DATETIME DEFAULT NULL",
        'iqama_expiry_date': "DATETIME DEFAULT NULL",
        'passport_expiry_date': "DATETIME DEFAULT NULL",
        'other_allowances': "REAL DEFAULT 0.0",
        'bank_name': "TEXT DEFAULT NULL"
    }
    
    cursor.execute("PRAGMA table_info(employees)")
    existing_emp_cols = [col[1] for col in cursor.fetchall()]
    
    for col_name, col_def in emp_columns.items():
        if col_name not in existing_emp_cols:
            print(f"  Adding to employees: {col_name} ({col_def})")
            try:
                cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_def}")
                conn.commit()
            except sqlite3.OperationalError as err:
                print(f"  Error adding {col_name}: {err}")

    # 3. Migration for PAYROLLS table
    payroll_columns = {
        'basic_salary': "REAL DEFAULT 0.0",
        'housing_allowance': "REAL DEFAULT 0.0",
        'transport_allowance': "REAL DEFAULT 0.0",
        'other_allowances': "REAL DEFAULT 0.0",
        'employee_saned': "REAL DEFAULT 0.0",
        'employer_saned': "REAL DEFAULT 0.0",
        'hazards_fee': "REAL DEFAULT 0.0",
        'vat_tally': "REAL DEFAULT 0.0",
        'employer_sif': "REAL DEFAULT 0.0",
        'employer_gosi': "REAL DEFAULT 0.0",
        'employee_gosi': "REAL DEFAULT 0.0",
        'wps_status': "TEXT DEFAULT 'Pending'",
        'sif_batch_id': "TEXT DEFAULT NULL"
    }
    
    cursor.execute("PRAGMA table_info(payrolls)")
    existing_pay_cols = [col[1] for col in cursor.fetchall()]
    
    for col_name, col_def in payroll_columns.items():
        if col_name not in existing_pay_cols:
            print(f"  Adding to payrolls: {col_name} ({col_def})")
            try:
                cursor.execute(f"ALTER TABLE payrolls ADD COLUMN {col_name} {col_def}")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    # 4. Create Invoicing tables if not exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        vat_number TEXT NULL,
        cr_number TEXT NULL,
        email TEXT NULL,
        phone TEXT NULL,
        address TEXT NULL,
        city TEXT DEFAULT 'Riyadh',
        country TEXT DEFAULT 'Saudi Arabia',
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        invoice_type TEXT DEFAULT 'Tax Invoice',
        issue_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        due_date DATETIME NULL,
        customer_id INTEGER NOT NULL,
        subtotal REAL DEFAULT 0.0,
        vat_total REAL DEFAULT 0.0,
        total_amount REAL DEFAULT 0.0,
        paid_amount REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Issued',
        notes TEXT NULL,
        zatca_qr_code TEXT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        beneficiary_name TEXT NULL,
        quantity REAL DEFAULT 1.0,
        unit_price REAL DEFAULT 0.0,
        govt_fee REAL DEFAULT 0.0,
        service_charge REAL DEFAULT 0.0,
        vat_rate REAL DEFAULT 0.15,
        vat_amount REAL DEFAULT 0.0,
        subtotal REAL DEFAULT 0.0,
        total_amount REAL DEFAULT 0.0
    )
    """)
    conn.commit()

    # Migration for invoice_items table
    inv_item_columns = {
        'beneficiary_name': "TEXT DEFAULT NULL",
        'govt_fee': "REAL DEFAULT 0.0",
        'service_charge': "REAL DEFAULT 0.0"
    }
    cursor.execute("PRAGMA table_info(invoice_items)")
    existing_item_cols = [col[1] for col in cursor.fetchall()]
    for col_name, col_def in inv_item_columns.items():
        if col_name not in existing_item_cols:
            try:
                cursor.execute(f"ALTER TABLE invoice_items ADD COLUMN {col_name} {col_def}")
                conn.commit()
            except Exception as e:
                pass
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalog_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        description TEXT NULL,
        unit_price REAL DEFAULT 0.0,
        category TEXT DEFAULT 'Services',
        is_active INTEGER DEFAULT 1
    )
    """)
    conn.commit()
    
    conn.close()
    print("\n[OK] Database schema migration completed successfully!")

if __name__ == "__main__":
    check_and_migrate_database()