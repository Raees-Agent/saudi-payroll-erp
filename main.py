"""
Main FastAPI application for HR & Payroll ERP System - Saudi Enterprise Edition
"""

from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import sys
sys.path.insert(0, '.')

from database import Base, engine, Employee, AttendanceRecord, PayrollRecord, CompanySettings, SessionLocal
from payroll import (
    calculate_payroll, process_monthly_payrolls, calculate_gosi_contributions,
    calculate_eosg, generate_sama_wps_sif, get_expiring_documents, calculate_saudization_ratio
)
from rag_engine import query_rag_system

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Saudi Enterprise HR & Payroll ERP API", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_employee(e: Employee) -> dict:
    return {
        "id": e.id,
        "employee_id": e.employee_id,
        "first_name": e.first_name,
        "last_name": e.last_name,
        "employee_name": e.employee_name,
        "email": e.email,
        "phone": e.phone,
        "department": e.department,
        "position": e.position,
        "nationality_type": e.nationality_type or "Expat",
        "contract_type": e.contract_type or "Indefinite",
        "iqama_id": e.iqama_id,
        "passport_number": e.passport_number,
        "basic_salary": e.basic_salary or e.base_salary,
        "housing_allowance": e.housing_allowance or 0.0,
        "transport_allowance": e.transport_allowance or 0.0,
        "other_allowances": e.other_allowances or 0.0,
        "base_salary": e.base_salary,
        "hourly_rate": e.hourly_rate,
        "hire_date": e.hire_date.strftime("%Y-%m-%d") if e.hire_date else None,
        "joining_date": e.joining_date.strftime("%Y-%m-%d") if e.joining_date else None,
        "iqama_expiry_date": e.iqama_expiry_date.strftime("%Y-%m-%d") if e.iqama_expiry_date else None,
        "passport_expiry_date": e.passport_expiry_date.strftime("%Y-%m-%d") if e.passport_expiry_date else None,
        "bank_name": e.bank_name,
        "iban_number": e.iban_number,
        "bank_code": e.bank_code,
        "is_active": bool(e.is_active)
    }


# ==================== EMPLOYEE ROUTES ====================

@app.get("/api/employees", response_model=List[dict])
def get_employees(db: Session = Depends(get_db)):
    """Get all active employees"""
    employees = db.query(Employee).filter(Employee.is_active == 1).all()
    return [serialize_employee(e) for e in employees]


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    """Get employee by ID"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return serialize_employee(employee)


@app.post("/api/employees/")
def create_employee(data: dict):
    """Create a new employee with full Saudi HR fields"""
    db = SessionLocal()
    try:
        existing = db.query(Employee).filter(Employee.employee_id == data["employee_id"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID already exists")

        basic_sal = float(data.get("basic_salary", data.get("base_salary", 0.0)))
        housing_sal = float(data.get("housing_allowance", 0.0))
        transport_sal = float(data.get("transport_allowance", 0.0))
        other_sal = float(data.get("other_allowances", 0.0))
        base_sal = basic_sal + housing_sal + transport_sal + other_sal

        def parse_dt(dt_str):
            if not dt_str:
                return None
            try:
                return datetime.fromisoformat(dt_str)
            except:
                return None

        new_employee = Employee(
            employee_id=data["employee_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data.get("email"),
            phone=data.get("phone"),
            department=data.get("department", "General Operations"),
            position=data.get("position", "Staff"),
            nationality_type=data.get("nationality_type", "Expat"),
            contract_type=data.get("contract_type", "Indefinite"),
            iqama_id=data.get("iqama_id"),
            passport_number=data.get("passport_number"),
            basic_salary=basic_sal,
            housing_allowance=housing_sal,
            transport_allowance=transport_sal,
            other_allowances=other_sal,
            base_salary=base_sal if base_sal > 0 else float(data.get("base_salary", 5000.0)),
            hourly_rate=float(data.get("hourly_rate", basic_sal / 208.0 if basic_sal else 25.0)),
            joining_date=parse_dt(data.get("joining_date")) or datetime.utcnow(),
            iqama_expiry_date=parse_dt(data.get("iqama_expiry_date")),
            passport_expiry_date=parse_dt(data.get("passport_expiry_date")),
            bank_name=data.get("bank_name"),
            iban_number=data.get("iban_number"),
            bank_code=data.get("bank_code"),
            is_active=1 if data.get("is_active", True) else 0
        )
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        return {"message": "Employee registered successfully", "employee": serialize_employee(new_employee)}
    finally:
        db.close()


@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    """Delete an employee"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    db.delete(employee)
    db.commit()
    return {"message": "Employee deleted successfully"}


@app.put("/api/employees/{employee_id}")
def update_employee(employee_id: int, employee_data: dict, db: Session = Depends(get_db)):
    """Update an employee"""
    existing = db.query(Employee).filter(Employee.id == employee_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    for field, value in employee_data.items():
        if hasattr(existing, field):
            if "date" in field and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except:
                    pass
            setattr(existing, field, value)
    
    db.commit()
    db.refresh(existing)
    return {"message": "Employee updated successfully", "employee": serialize_employee(existing)}


# ==================== ATTENDANCE ROUTES ====================

@app.get("/api/attendance", response_model=List[dict])
def get_attendance(
    limit: int = 100,
    offset: int = 0,
    date_from: str = None,
    date_to: str = None,
    employee_id: int = None,
    db: Session = Depends(get_db)
):
    """Get attendance records with optional filters"""
    query = db.query(AttendanceRecord).filter(AttendanceRecord.employee_id == employee_id) if employee_id else db.query(AttendanceRecord)

    if date_from:
        query = query.filter(AttendanceRecord.date >= date_from)
    if date_to:
        query = query.filter(AttendanceRecord.date <= date_to)

    records = query.order_by(AttendanceRecord.date.desc(), AttendanceRecord.id.desc()).limit(limit).offset(offset).all()
    
    return [{
        "id": r.id,
        "employee_id": r.employee_id,
        "date": r.date.strftime("%Y-%m-%d"),
        "check_in": r.check_in.strftime("%Y-%m-%d %H:%M") if r.check_in else None,
        "check_out": r.check_out.strftime("%Y-%m-%d %H:%M") if r.check_out else None,
        "hours_worked": r.hours_worked,
        "attendance_status": r.attendance_status,
        "overtime_hours": r.overtime_hours
    } for r in records]


@app.post("/api/attendance/")
def create_attendance(attendance_data: dict):
    """Create an attendance record"""
    db = SessionLocal()
    try:
        employee = db.query(Employee).filter(Employee.id == attendance_data["employee_id"]).first()
        if not employee or not employee.is_active:
            raise HTTPException(status_code=404, detail="Employee not found or inactive")

        check_in = attendance_data.get("check_in")
        check_out = attendance_data.get("check_out")
        
        if check_in and check_out:
            try:
                check_in_dt = datetime.fromisoformat(check_in)
                check_out_dt = datetime.fromisoformat(check_out)
                hours_worked = (check_out_dt - check_in_dt).total_seconds() / 3600
            except:
                hours_worked = float(attendance_data.get("hours_worked", 8.0))
        else:
            hours_worked = float(attendance_data.get("hours_worked", 8.0))
        
        overtime = max(0.0, hours_worked - 8.0) if hours_worked > 0 else 0.0
        date_str = attendance_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        try:
            date_obj = datetime.fromisoformat(date_str)
        except:
            date_obj = datetime.combine(datetime.date.today(), datetime.time.min)
        
        new_record = AttendanceRecord(
            employee_id=attendance_data["employee_id"],
            date=date_obj,
            hours_worked=float(hours_worked),
            overtime_hours=float(overtime),
            attendance_status=attendance_data.get("attendance_status", "Regular")
        )

        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return {"message": "Attendance recorded successfully", "record": new_record}
    finally:
        db.close()


# ==================== PAYROLL & WPS ROUTES ====================

@app.post("/api/payroll/calculate/{employee_id}")
def calculate_employee_payroll(employee_id: int):
    """Calculate payroll for a specific employee"""
    return calculate_payroll(employee_id)


@app.get("/api/payroll/monthly/bulk")
def calculate_all_payrolls():
    """Calculate payroll for all active employees for current month"""
    db = SessionLocal()
    try:
        result = process_monthly_payrolls(db)
        return {"message": "Payroll calculated successfully", "records_processed": result}
    finally:
        db.close()


@app.get("/api/payroll/{employee_id}")
def get_payroll_history(employee_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get payroll history for an employee"""
    payrolls = db.query(PayrollRecord).filter(
        PayrollRecord.employee_id == employee_id
    ).order_by(PayrollRecord.month.desc()).limit(limit).all()
    
    return [{
        "id": p.id,
        "employee_id": p.employee_id,
        "month": p.month.strftime("%Y-%m") if p.month else None,
        "basic_salary": p.basic_salary,
        "housing_allowance": p.housing_allowance,
        "transport_allowance": p.transport_allowance,
        "overtime_pay": p.overtime_pay,
        "gross_salary": p.gross_salary,
        "employee_gosi": p.employee_gosi,
        "employer_gosi": p.employer_gosi,
        "deductions": p.deductions,
        "net_salary": p.net_salary,
        "status": p.status,
        "wps_status": p.wps_status
    } for p in payrolls]


@app.post("/api/wps/generate-sif")
def generate_wps_sif(month: Optional[str] = None):
    """Generate official SAMA / Mudad compliant WPS SIF file content"""
    return generate_sama_wps_sif(month)


# ==================== SAUDI LABOR COMPLIANCE ROUTES ====================

@app.get("/api/compliance/nitaqat")
def get_nitaqat_metrics(db: Session = Depends(get_db)):
    """Get establishment Saudization ratio and MHRSD Nitaqat tier"""
    return calculate_saudization_ratio(db)


@app.get("/api/compliance/documents/expiring")
def get_expiring_doc_alerts(days: int = 60, db: Session = Depends(get_db)):
    """Get alerts for Iqama and Passport expiry dates"""
    return get_expiring_documents(days, db)


@app.post("/api/eosg/calculate")
def calculate_end_of_service(data: dict):
    """Calculate End-of-Service Gratuity (EOSG) adhering to Saudi Labor Law Articles 84 & 85"""
    basic_sal = float(data.get("basic_salary", 5000.0))
    housing_sal = float(data.get("housing_allowance", 0.0))
    transport_sal = float(data.get("transport_allowance", 0.0))
    other_sal = float(data.get("other_allowances", 0.0))
    service_years = float(data.get("years_of_service", 3.0))
    reason = data.get("separation_reason", "Resignation by Employee")
    contract = data.get("contract_type", "Indefinite")
    
    return calculate_eosg(
        basic_salary=basic_sal,
        housing_allowance=housing_sal,
        transport_allowance=transport_sal,
        other_allowances=other_sal,
        years_of_service=service_years,
        separation_reason=reason,
        contract_type=contract
    )


# ==================== COMPANY SETTINGS ROUTES ====================

@app.get("/api/company/settings")
def get_company_settings(db: Session = Depends(get_db)):
    """Get establishment details (CR, Qiwa ID, Bank Account, VAT Number)"""
    comp = db.query(CompanySettings).first()
    if not comp:
        comp = CompanySettings()
        db.add(comp)
        db.commit()
        db.refresh(comp)
    return {
        "id": comp.id,
        "establishment_name": comp.establishment_name,
        "cr_number": comp.cr_number,
        "qiwa_id": comp.qiwa_id,
        "gosi_reg_number": comp.gosi_reg_number,
        "vat_number": comp.vat_number,
        "bank_code": comp.bank_code,
        "company_iban": comp.company_iban
    }


@app.put("/api/company/settings")
def update_company_settings(data: dict, db: Session = Depends(get_db)):
    """Update establishment details"""
    comp = db.query(CompanySettings).first()
    if not comp:
        comp = CompanySettings()
        db.add(comp)
    
    for k, v in data.items():
        if hasattr(comp, k):
            setattr(comp, k, v)
            
    db.commit()
    db.refresh(comp)
    return {"message": "Company settings updated successfully", "settings": data}


# ==================== DASHBOARD STATS ROUTE ====================

@app.get("/api/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get full executive dashboard statistics"""
    total_employees = db.query(Employee).filter(Employee.is_active == 1).count()
    
    departments = db.query(func.count(Employee.id), Employee.department).filter(
        Employee.is_active == 1,
        Employee.department != None,
        Employee.department != ''
    ).group_by(Employee.department).all()
    
    attendance_this_month = db.query(AttendanceRecord).filter(
        AttendanceRecord.date >= datetime.now().replace(day=1)
    ).count()

    payroll_records = db.query(PayrollRecord).all()
    total_gross = sum(p.gross_salary for p in payroll_records)
    total_net = sum(p.net_salary for p in payroll_records)
    
    nitaqat = calculate_saudization_ratio(db)
    doc_alerts = get_expiring_documents(60, db)
    
    return {
        "total_employees": total_employees,
        "saudi_count": nitaqat["saudi_count"],
        "expat_count": nitaqat["expat_count"],
        "saudization_percentage": nitaqat["saudization_percentage"],
        "nitaqat_tier": nitaqat["nitaqat_tier"],
        "expiring_document_count": len(doc_alerts),
        "departments": [{"department": d[1], "count": d[0]} for d in departments],
        "attendance_this_month": attendance_this_month,
        "total_gross_paid": round(total_gross, 2),
        "total_net_paid": round(total_net, 2)
    }


# ==================== INVOICING & BILLING ROUTES ====================

from database import Customer, Invoice, InvoiceItem, CatalogItem
from invoicing import create_invoice, record_invoice_payment, get_invoicing_kpis, generate_customer_statement

@app.get("/api/invoicing/kpis")
def get_invoicing_summary_kpis(db: Session = Depends(get_db)):
    """Get executive billing KPIs (Total Invoiced, Paid, Outstanding, Overdue)"""
    return get_invoicing_kpis(db)


@app.get("/api/invoicing/statement/{customer_id}")
def get_statement_of_account(customer_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None, db: Session = Depends(get_db)):
    """Generate Statement of Account (SOA) for a B2B Client"""
    return generate_customer_statement(customer_id, start_date, end_date, db)


@app.get("/api/invoicing/customers")
def get_customers(db: Session = Depends(get_db)):
    """Get all B2B Customers"""
    customers = db.query(Customer).filter(Customer.is_active == 1).all()
    return [{
        "id": c.id,
        "customer_name": c.customer_name,
        "vat_number": c.vat_number,
        "cr_number": c.cr_number,
        "email": c.email,
        "phone": c.phone,
        "address": c.address,
        "city": c.city,
        "country": c.country
    } for c in customers]


@app.post("/api/invoicing/customers")
def create_customer(data: dict, db: Session = Depends(get_db)):
    """Create a new B2B customer profile"""
    new_cust = Customer(
        customer_name=data["customer_name"],
        vat_number=data.get("vat_number"),
        cr_number=data.get("cr_number"),
        email=data.get("email"),
        phone=data.get("phone"),
        address=data.get("address"),
        city=data.get("city", "Riyadh"),
        country=data.get("country", "Saudi Arabia")
    )
    db.add(new_cust)
    db.commit()
    db.refresh(new_cust)
    return {"message": "Customer created successfully", "customer_id": new_cust.id}


@app.get("/api/invoicing/invoices")
def get_invoices(db: Session = Depends(get_db)):
    """Get all invoices with customer details"""
    invoices = db.query(Invoice).order_by(Invoice.issue_date.desc()).all()
    res = []
    for inv in invoices:
        cust = db.query(Customer).filter(Customer.id == inv.customer_id).first()
        res.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_type": inv.invoice_type,
            "issue_date": inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else None,
            "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
            "customer_id": inv.customer_id,
            "customer_name": cust.customer_name if cust else "N/A",
            "customer_vat": cust.vat_number if cust else "N/A",
            "subtotal": inv.subtotal,
            "vat_total": inv.vat_total,
            "total_amount": inv.total_amount,
            "paid_amount": inv.paid_amount,
            "status": inv.status,
            "zatca_qr_code": inv.zatca_qr_code
        })
    return res


@app.get("/api/invoicing/invoices/{invoice_id}")
def get_invoice_details(invoice_id: int, db: Session = Depends(get_db)):
    """Get complete invoice details with itemized line items and ZATCA QR code"""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    cust = db.query(Customer).filter(Customer.id == inv.customer_id).first()
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()
    company = db.query(CompanySettings).first()
    
    return {
        "invoice": {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_type": inv.invoice_type,
            "issue_date": inv.issue_date.strftime("%Y-%m-%d %H:%M") if inv.issue_date else None,
            "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
            "subtotal": inv.subtotal,
            "vat_total": inv.vat_total,
            "total_amount": inv.total_amount,
            "paid_amount": inv.paid_amount,
            "status": inv.status,
            "notes": inv.notes,
            "zatca_qr_code": inv.zatca_qr_code
        },
        "seller": {
            "name": company.establishment_name if company else "Saudi Enterprise Corp",
            "cr_number": company.cr_number if company else "1010000000",
            "vat_number": company.vat_number if company else "310000000000003",
            "iban": company.company_iban if company else ""
        },
        "customer": {
            "name": cust.customer_name if cust else "N/A",
            "vat_number": cust.vat_number if cust else "N/A",
            "cr_number": cust.cr_number if cust else "N/A",
            "address": cust.address if cust else "N/A",
            "city": cust.city if cust else "Riyadh"
        },
        "items": [{
            "id": i.id,
            "description": i.description,
            "beneficiary_name": i.beneficiary_name,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
            "govt_fee": i.govt_fee,
            "service_charge": i.service_charge,
            "vat_rate": i.vat_rate,
            "vat_amount": i.vat_amount,
            "subtotal": i.subtotal,
            "total_amount": i.total_amount
        } for i in items]
    }


@app.post("/api/invoicing/invoices")
def create_new_invoice(payload: dict = Body(...)):
    """Create a new ZATCA Tax Invoice"""
    inv_data = payload.get("invoice", {})
    line_items = payload.get("items", [])
    return create_invoice(inv_data, line_items)


@app.post("/api/invoicing/invoices/{invoice_id}/pay")
def pay_invoice(invoice_id: int, payload: dict = Body(...)):
    """Record payment for an invoice"""
    amount = float(payload.get("amount", 0.0))
    return record_invoice_payment(invoice_id, amount)


@app.get("/api/invoicing/catalog")
def get_catalog_items(db: Session = Depends(get_db)):
    """Get item catalog for invoice building"""
    items = db.query(CatalogItem).filter(CatalogItem.is_active == 1).all()
    return [{
        "id": c.id,
        "item_name": c.item_name,
        "description": c.description,
        "unit_price": c.unit_price,
        "category": c.category
    } for c in items]


@app.post("/api/invoicing/catalog")
def create_catalog_item(data: dict, db: Session = Depends(get_db)):
    """Add a new item to catalog"""
    item = CatalogItem(
        item_name=data["item_name"],
        description=data.get("description"),
        unit_price=float(data.get("unit_price", 0.0)),
        category=data.get("category", "Services")
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": "Catalog item added successfully", "item_id": item.id}


@app.get("/api/rag/query")
def rag_search(q: str, db: Session = Depends(get_db)):
    """Search Saudi ERP Knowledge Base & Real-time Database using RAG Engine"""
    return query_rag_system(q, db=db)


@app.post("/api/rag/query")
def rag_search_post(data: dict, db: Session = Depends(get_db)):
    """Search Saudi ERP Knowledge Base & Real-time Database using RAG Engine"""
    q = data.get("query", "")
    return query_rag_system(q, db=db)


# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Saudi Enterprise HR, Payroll & Invoicing ERP System API",
        "version": "2.1.0",
        "docs": "/docs",
        "streamlit_dashboard": "Run: streamlit run app.py"
    }
