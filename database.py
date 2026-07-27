"""
Database models and initialization for HR & Payroll ERP System
Uses SQLite with SQLAlchemy ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./payroll_db.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Employee Model
class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    phone = Column(String(20))
    department = Column(String(100))
    position = Column(String(100))
    base_salary = Column(Float, nullable=False)
    hourly_rate = Column(Float)
    hire_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)
    
    # Saudi Enterprise HR & WPS Compliance fields
    nationality_type = Column(String(20), default="Expat")  # Saudi, Expat
    contract_type = Column(String(20), default="Indefinite") # Indefinite, Fixed
    iqama_id = Column(String(50), nullable=True)             # Iqama ID or National ID
    passport_number = Column(String(50), nullable=True)
    joining_date = Column(DateTime, default=datetime.utcnow)
    iqama_expiry_date = Column(DateTime, nullable=True)
    passport_expiry_date = Column(DateTime, nullable=True)
    
    # Salary Component breakdown (SAR)
    basic_salary = Column(Float, default=0.0, nullable=True)
    housing_allowance = Column(Float, default=0.0, nullable=True)
    transport_allowance = Column(Float, default=0.0, nullable=True)
    other_allowances = Column(Float, default=0.0, nullable=True)
    gosi_deduction = Column(Float, default=0.0, nullable=True)
    other_deductions = Column(Float, default=0.0, nullable=True)
    
    # Bank & Payment Info
    bank_name = Column(String(100), nullable=True)
    iban_number = Column(String(50), nullable=True)
    bank_code = Column(String(20), nullable=True)
    company_id = Column(String(50), nullable=True)

    @property
    def employee_name(self):
        return f"{self.first_name} {self.last_name}"


# Attendance Model
class AttendanceRecord(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    check_in = Column(DateTime)
    check_out = Column(DateTime)
    hours_worked = Column(Float, default=0.0)
    attendance_status = Column(String(20), default="Regular")  # Regular, Leave, Late, Absent
    overtime_hours = Column(Float, default=0.0)


# Payroll Model
class PayrollRecord(Base):
    __tablename__ = "payrolls"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Component Earnings
    basic_salary = Column(Float, default=0.0, nullable=True)
    housing_allowance = Column(Float, default=0.0, nullable=True)
    transport_allowance = Column(Float, default=0.0, nullable=True)
    other_allowances = Column(Float, default=0.0, nullable=True)
    regular_hours_pay = Column(Float, default=0.0)
    overtime_pay = Column(Float, default=0.0)
    bonuses = Column(Float, default=0.0)
    gross_salary = Column(Float, default=0.0)
    
    # Itemized Deductions & Contributions (GOSI / SANED / Hazards)
    deductions = Column(Float, default=0.0)  # Total employee deductions
    employee_gosi = Column(Float, default=0.0, nullable=True)
    employee_saned = Column(Float, default=0.0, nullable=True)
    employer_gosi = Column(Float, default=0.0, nullable=True)
    employer_saned = Column(Float, default=0.0, nullable=True)
    employer_sif = Column(Float, default=0.0, nullable=True)
    hazards_fee = Column(Float, default=0.0, nullable=True)
    
    net_salary = Column(Float, default=0.0)
    status = Column(String(20), default="pending")  # pending, processed, paid
    
    # Saudi Compliance & Tracking
    govt_fee = Column(Float, default=0.0, nullable=True)
    tax_rate = Column(Float, default=0.0, nullable=True)
    service_type = Column(String(100), nullable=True)
    file_url = Column(String(500), nullable=True)
    vat_tally = Column(Float, default=0.0, nullable=True)
    wps_status = Column(String(20), default="Pending") # Pending, Generated, Submitted
    sif_batch_id = Column(String(100), nullable=True)


# Company / Establishment Settings Model
class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True)
    establishment_name = Column(String(200), default="Saudi Enterprise Corporation")
    cr_number = Column(String(50), default="1010000000")              # Commercial Registration Number
    qiwa_id = Column(String(50), default="QIW-998877")                # Qiwa / MOL ID
    gosi_reg_number = Column(String(50), default="998877665")         # GOSI Registration ID
    vat_number = Column(String(50), default="310000000000003")         # 15-digit Tax VAT Number
    bank_code = Column(String(20), default="RIBL")                    # SAMA Bank Code (e.g., RJHI, RIBL, NCBK)
    company_iban = Column(String(50), default="SA0000000000000000000000")
    cr_expiry_date = Column(DateTime, nullable=True)


# Customer / B2B Client Model
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(200), nullable=False)
    vat_number = Column(String(50), nullable=True)     # 15-digit ZATCA VAT Number
    cr_number = Column(String(50), nullable=True)      # Commercial Registration Number
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(300), nullable=True)
    city = Column(String(100), default="Riyadh")
    country = Column(String(100), default="Saudi Arabia")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


# ZATCA Compliant Invoice Model
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False) # e.g. INV-2026-0001
    invoice_type = Column(String(50), default="Tax Invoice")          # Tax Invoice, Simplified Tax Invoice
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Financial Totals (SAR)
    subtotal = Column(Float, default=0.0)
    vat_total = Column(Float, default=0.0)      # 15% ZATCA VAT
    total_amount = Column(Float, default=0.0)   # Net Total with VAT
    paid_amount = Column(Float, default=0.0)
    
    status = Column(String(20), default="Issued")  # Draft, Issued, Paid, Partially Paid, Overdue, Cancelled
    notes = Column(Text, nullable=True)
    zatca_qr_code = Column(Text, nullable=True)    # Base64 ZATCA TLV string
    created_at = Column(DateTime, default=datetime.utcnow)


# Invoice Itemized Line Items
class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String(300), nullable=False)
    beneficiary_name = Column(String(200), nullable=True) # End Beneficiary (Employee / Entity)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    govt_fee = Column(Float, default=0.0)                 # Government Fee (SAR)
    service_charge = Column(Float, default=0.0)           # Service / Handling Charge (SAR)
    vat_rate = Column(Float, default=0.15)                 # 15% VAT
    vat_amount = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)



# Product & Service Catalog Model
class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    unit_price = Column(Float, default=0.0)
    category = Column(String(100), default="Services")
    is_active = Column(Integer, default=1)


