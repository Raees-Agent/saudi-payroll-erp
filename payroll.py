"""
Payroll calculation logic for HR & Payroll ERP System - Saudi Enterprise Edition
Includes GOSI (Saudi vs Expat), EOSG (Article 84/85), SAMA WPS/SIF Generator, Document Expiry Tracking, and Nitaqat Analytics.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import calendar
import pandas as pd
from database import Employee, AttendanceRecord, PayrollRecord, CompanySettings, SessionLocal, engine, Base

# ============================================
# SAUDI ARABIA GOSI & SANED & HAZARDS RATES
# ============================================
# Capped at SAR 45,000 for Basic + Housing
GOSI_SALARY_CAP = 45000.0

# Saudi Nationals Rates:
SAUDI_EMP_GOSI = 0.09        # 9.0% Pension
SAUDI_EMP_SANED = 0.0075     # 0.75% Unemployment (SANED)
SAUDI_EMP_TOTAL = 0.0975     # 9.75% Total Employee Contribution

SAUDI_COMP_GOSI = 0.09       # 9.0% Pension
SAUDI_COMP_SANED = 0.0075    # 0.75% Unemployment (SANED)
SAUDI_COMP_HAZARDS = 0.02    # 2.0% Occupational Hazards
SAUDI_COMP_TOTAL = 0.1175    # 11.75% Total Employer Contribution

# Expat Rates:
EXPAT_EMP_TOTAL = 0.0        # 0.0% Employee Contribution
EXPAT_COMP_HAZARDS = 0.02    # 2.0% Employer Occupational Hazards


def calculate_gosi_contributions(basic_salary: float, housing_allowance: float = 0.0, 
                                 nationality_type: str = "Expat") -> Dict[str, float]:
    """
    Calculate Saudi GOSI, SANED, and Occupational Hazards contributions following MHRSD & GOSI rules.
    """
    gosi_base = min(max(0.0, basic_salary) + max(0.0, housing_allowance), GOSI_SALARY_CAP)
    is_saudi = (nationality_type.strip().lower() == "saudi")
    
    if is_saudi:
        emp_gosi = gosi_base * SAUDI_EMP_GOSI
        emp_saned = gosi_base * SAUDI_EMP_SANED
        emp_total = emp_gosi + emp_saned
        
        comp_gosi = gosi_base * SAUDI_COMP_GOSI
        comp_saned = gosi_base * SAUDI_COMP_SANED
        comp_hazards = gosi_base * SAUDI_COMP_HAZARDS
        comp_total = comp_gosi + comp_saned + comp_hazards
    else:
        emp_gosi = 0.0
        emp_saned = 0.0
        emp_total = 0.0
        
        comp_gosi = 0.0
        comp_saned = 0.0
        comp_hazards = gosi_base * EXPAT_COMP_HAZARDS
        comp_total = comp_hazards

    return {
        "is_saudi": is_saudi,
        "gosi_base": round(gosi_base, 2),
        "employee_gosi": round(emp_gosi, 2),
        "employee_saned": round(emp_saned, 2),
        "employee_total_deduction": round(emp_total, 2),
        "employer_gosi": round(comp_gosi, 2),
        "employer_saned": round(comp_saned, 2),
        "employer_hazards": round(comp_hazards, 2),
        "employer_total_contribution": round(comp_total, 2),
        # Legacy compatibility keys
        "employer_sif": round(comp_total, 2)
    }


# ============================================
# SAUDI LABOR LAW EOSG CALCULATOR (ART. 84 & 85)
# ============================================

def calculate_eosg(basic_salary: float, housing_allowance: float = 0.0,
                   transport_allowance: float = 0.0, other_allowances: float = 0.0,
                   years_of_service: float = 0.0,
                   separation_reason: str = "Resignation by Employee",
                   contract_type: str = "Indefinite") -> Dict[str, any]:
    """
    Calculate Saudi End-of-Service Gratuity (EOSG) adhering to Articles 84 and 85 of Saudi Labor Law.
    """
    monthly_wage = max(0.0, basic_salary) + max(0.0, housing_allowance) + max(0.0, transport_allowance) + max(0.0, other_allowances)
    
    if years_of_service <= 0 or monthly_wage <= 0:
        return {
            "monthly_wage": round(monthly_wage, 2),
            "years_of_service": round(years_of_service, 2),
            "base_gratuity": 0.0,
            "eligibility_percentage": 0.0,
            "final_eosg_payout": 0.0,
            "notes": "Insufficient tenure or wage"
        }

    # Base Gratuity Calculation (Half month salary for first 5 yrs, full month salary per yr for remaining)
    if years_of_service <= 5.0:
        base_gratuity = years_of_service * (monthly_wage / 2.0)
    else:
        base_gratuity = (5.0 * (monthly_wage / 2.0)) + ((years_of_service - 5.0) * monthly_wage)

    # Article 85 Resignation Payout Adjustment Factor
    reason_clean = separation_reason.strip().lower()
    is_resignation = "resignation" in reason_clean
    
    if not is_resignation or contract_type.lower() == "fixed":
        # Termination by employer, end of contract, force majeure = 100% entitlement
        payout_factor = 1.0
        clause = "Full Entitlement (Article 84)"
    else:
        # Resignation by Employee on Indefinite Contract (Article 85)
        if years_of_service < 2.0:
            payout_factor = 0.0
            clause = "No Entitlement (< 2 years resignation)"
        elif years_of_service <= 5.0:
            payout_factor = 1.0 / 3.0
            clause = "One-Third Entitlement (2-5 years resignation)"
        elif years_of_service < 10.0:
            payout_factor = 2.0 / 3.0
            clause = "Two-Thirds Entitlement (5-10 years resignation)"
        else:
            payout_factor = 1.0
            clause = "Full Entitlement (> 10 years resignation)"

    final_eosg = base_gratuity * payout_factor

    return {
        "monthly_wage": round(monthly_wage, 2),
        "years_of_service": round(years_of_service, 2),
        "base_gratuity": round(base_gratuity, 2),
        "eligibility_percentage": round(payout_factor * 100, 2),
        "final_eosg_payout": round(final_eosg, 2),
        "clause": clause
    }


# ============================================
# PAYROLL CALCULATION WITH FULL COMPLIANCE
# ============================================

def calculate_payroll(employee_id: int, db: Optional[Session] = None, 
                     auto_calculate_gross: bool = False):
    """
    Calculate monthly payroll for employee with Saudi GOSI, Allowances, Overtime, and VAT.
    """
    session = SessionLocal() if db is None else db
    
    try:
        employee = session.query(Employee).filter(
            Employee.id == employee_id,
            Employee.is_active == 1
        ).first()
        
        if not employee:
            return {"error": "Employee not found", "success": False}
        
        month = datetime.now()
        month_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month.month == 12:
            next_month_start = month.replace(year=month.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_month_start = month.replace(month=month.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
        attendance_records = session.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date >= month_start,
            AttendanceRecord.date < next_month_start
        ).all()
        
        total_regular_hours = 0.0
        total_overtime_hours = 0.0
        
        for r in attendance_records:
            total_regular_hours += min(r.hours_worked, 8.0)
            total_overtime_hours += max(0.0, r.hours_worked - 8.0)
            
        # Determine Salary Component Inputs
        basic_sal = employee.basic_salary if (employee.basic_salary and employee.basic_salary > 0) else employee.base_salary
        housing_sal = employee.housing_allowance or 0.0
        transport_sal = employee.transport_allowance or 0.0
        other_sal = employee.other_allowances or 0.0
        
        hourly_rate = employee.hourly_rate or (basic_sal / 208.0 if basic_sal else 0.0)
        overtime_pay = round(total_overtime_hours * hourly_rate * 1.5, 2)
        regular_hours_pay = round(total_regular_hours * hourly_rate, 2)
        
        gross_salary = round(basic_sal + housing_sal + transport_sal + other_sal + overtime_pay, 2)
        
        # Calculate GOSI
        gosi_res = calculate_gosi_contributions(basic_sal, housing_sal, employee.nationality_type or "Expat")
        
        employee_gosi_deduction = gosi_res["employee_total_deduction"]
        other_deductions = employee.other_deductions or 0.0
        total_deductions = employee_gosi_deduction + other_deductions
        
        net_salary = round(gross_salary - total_deductions, 2)
        
        # VAT Tally (15% applicable to corporate employer contributions)
        vat_tally = round((gross_salary + gosi_res["employer_total_contribution"]) * 0.15, 2)
        
        month_key = month.strftime("%Y-%m")
        
        existing_payroll = session.query(PayrollRecord).filter(
            PayrollRecord.employee_id == employee_id,
            PayrollRecord.month >= month_start,
            PayrollRecord.month < next_month_start
        ).first()
        
        if existing_payroll:
            existing_payroll.basic_salary = basic_sal
            existing_payroll.housing_allowance = housing_sal
            existing_payroll.transport_allowance = transport_sal
            existing_payroll.other_allowances = other_sal
            existing_payroll.regular_hours_pay = regular_hours_pay
            existing_payroll.overtime_pay = overtime_pay
            existing_payroll.gross_salary = gross_salary
            existing_payroll.deductions = total_deductions
            existing_payroll.employee_gosi = gosi_res["employee_gosi"]
            existing_payroll.employee_saned = gosi_res["employee_saned"]
            existing_payroll.employer_gosi = gosi_res["employer_gosi"]
            existing_payroll.employer_saned = gosi_res["employer_saned"]
            existing_payroll.employer_sif = gosi_res["employer_total_contribution"]
            existing_payroll.hazards_fee = gosi_res["employer_hazards"]
            existing_payroll.net_salary = net_salary
            existing_payroll.vat_tally = vat_tally
            existing_payroll.status = "processed"
            existing_payroll.wps_status = "Generated"
            target_payroll = existing_payroll
        else:
            new_payroll = PayrollRecord(
                employee_id=employee_id,
                month=month,
                basic_salary=basic_sal,
                housing_allowance=housing_sal,
                transport_allowance=transport_sal,
                other_allowances=other_sal,
                regular_hours_pay=regular_hours_pay,
                overtime_pay=overtime_pay,
                gross_salary=gross_salary,
                deductions=total_deductions,
                employee_gosi=gosi_res["employee_gosi"],
                employee_saned=gosi_res["employee_saned"],
                employer_gosi=gosi_res["employer_gosi"],
                employer_saned=gosi_res["employer_saned"],
                employer_sif=gosi_res["employer_total_contribution"],
                hazards_fee=gosi_res["employer_hazards"],
                net_salary=net_salary,
                vat_tally=vat_tally,
                status="processed",
                wps_status="Generated"
            )
            session.add(new_payroll)
            target_payroll = new_payroll
        
        session.commit()
        session.refresh(target_payroll)
        
        return {
            "success": True,
            "employee_id": employee_id,
            "employee_name": employee.employee_name,
            "nationality_type": employee.nationality_type or "Expat",
            "month": month_key,
            "basic_salary": basic_sal,
            "housing_allowance": housing_sal,
            "transport_allowance": transport_sal,
            "other_allowances": other_sal,
            "overtime_pay": overtime_pay,
            "gross_salary": gross_salary,
            "employee_gosi": gosi_res["employee_gosi"],
            "employee_saned": gosi_res["employee_saned"],
            "total_deductions": total_deductions,
            "employer_gosi": gosi_res["employer_gosi"],
            "employer_saned": gosi_res["employer_saned"],
            "employer_hazards": gosi_res["employer_hazards"],
            "employer_total_contribution": gosi_res["employer_total_contribution"],
            "net_salary": net_salary,
            "vat_tally": vat_tally,
            "status": target_payroll.status,
            "wps_status": target_payroll.wps_status
        }
        
    except Exception as e:
        session.rollback()
        return {"error": str(e), "success": False}
    finally:
        if db is None:
            session.close()


def process_monthly_payrolls(db: Session):
    """Process payroll for all active employees for current month with full compliance"""
    employees = db.query(Employee).filter(Employee.is_active == 1).all()
    processed_count = 0
    for employee in employees:
        try:
            result = calculate_payroll(employee.id, db)
            if result.get("success"):
                processed_count += 1
        except Exception as e:
            print(f"Error processing payroll for employee {employee.employee_id}: {e}")
    return processed_count


# ============================================
# OFFICIAL SAMA & MUDAD WPS SIF GENERATOR
# ============================================

def generate_sama_wps_sif(month: str = None, db: Optional[Session] = None) -> Dict[str, any]:
    """
    Generate an official SAMA / Mudad compliant WPS .SIF file format.
    """
    session = SessionLocal() if db is None else db
    if not month:
        month = datetime.now().strftime("%Y-%m")
        
    try:
        company = session.query(CompanySettings).first()
        if not company:
            company = CompanySettings()
            
        try:
            month_dt = datetime.strptime(month, "%Y-%m")
        except ValueError:
            month_dt = datetime.now()
            
        m_start = month_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_dt.month == 12:
            m_end = month_dt.replace(year=month_dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            m_end = month_dt.replace(month=month_dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

        payrolls = session.query(PayrollRecord).filter(
            PayrollRecord.month >= m_start,
            PayrollRecord.month < m_end
        ).all()
        
        if not payrolls:
            # Attempt to process payrolls first
            process_monthly_payrolls(session)
            payrolls = session.query(PayrollRecord).filter(
                PayrollRecord.month >= m_start,
                PayrollRecord.month < m_end
            ).all()

        lines = []
        now_str = datetime.now().strftime("%Y%m%d")
        now_time = datetime.now().strftime("%H%M")
        
        total_salaries = sum(p.net_salary for p in payrolls)
        record_count = len(payrolls)
        
        # SAMA SIF Header
        # HEADER,CR_NO,BANK_CODE,DATE,TIME,TOTAL_NET,RECORDS_COUNT,SAR
        header = f"HEADER,{company.cr_number},{company.bank_code},{now_str},{now_time},{total_salaries:.2f},{record_count},SAR"
        lines.append(header)
        
        # Employee Detail Lines
        for p in payrolls:
            emp = session.query(Employee).filter(Employee.id == p.employee_id).first()
            if not emp:
                continue
            
            emp_nat_id = emp.iqama_id or emp.employee_id
            iban = emp.iban_number or company.company_iban
            bank_code = emp.bank_code or company.bank_code
            basic = p.basic_salary or emp.base_salary
            housing = p.housing_allowance or 0.0
            other_allow = (p.transport_allowance or 0.0) + (p.other_allowances or 0.0) + (p.overtime_pay or 0.0)
            deductions = p.deductions or 0.0
            net = p.net_salary
            
            # EMPLOYEE,EMP_CODE,IQAMA_ID,IBAN,BANK_CODE,BASIC,HOUSING,OTHER_ALLOW,DEDUCTIONS,NET_SALARY,SAR
            emp_line = f"EMPLOYEE,{emp.employee_id},{emp_nat_id},{iban},{bank_code},{basic:.2f},{housing:.2f},{other_allow:.2f},{deductions:.2f},{net:.2f},SAR"
            lines.append(emp_line)

        sif_content = "\n".join(lines)
        file_name = f"WPS_SIF_{company.cr_number}_{month.replace('-', '')}.sif"
        
        return {
            "success": True,
            "file_name": file_name,
            "record_count": record_count,
            "total_salaries_sar": round(total_salaries, 2),
            "sif_content": sif_content
        }
    except Exception as e:
        return {"error": str(e), "success": False}
    finally:
        if db is None:
            session.close()


# Alias for legacy compatibility
def export_payroll_to_wps_sif(employee_id: int, month: str = None) -> Dict[str, any]:
    sif_res = generate_sama_wps_sif(month)
    if sif_res.get("success"):
        return {"success": True, "wps_data": sif_res, "message": "WPS SIF export successful"}
    return sif_res


# ============================================
# COMPLIANCE: EXPIRED DOCUMENTS & NITAQAT
# ============================================

def get_expiring_documents(days_ahead: int = 60, db: Optional[Session] = None) -> List[Dict[str, any]]:
    """Scan Iqama and Passport expiry dates for active employees"""
    session = SessionLocal() if db is None else db
    try:
        now = datetime.now()
        target_date = now + timedelta(days=days_ahead)
        
        employees = session.query(Employee).filter(Employee.is_active == 1).all()
        alerts = []
        
        for emp in employees:
            if emp.iqama_expiry_date:
                days_left = (emp.iqama_expiry_date - now).days
                if days_left <= days_ahead:
                    alerts.append({
                        "employee_id": emp.employee_id,
                        "employee_name": emp.employee_name,
                        "doc_type": "Iqama / National ID",
                        "doc_number": emp.iqama_id or "N/A",
                        "expiry_date": emp.iqama_expiry_date.strftime("%Y-%m-%d"),
                        "days_remaining": days_left,
                        "status": "EXPIRED" if days_left < 0 else ("URGENT" if days_left <= 15 else "WARNING")
                    })
            if emp.passport_expiry_date:
                days_left = (emp.passport_expiry_date - now).days
                if days_left <= days_ahead:
                    alerts.append({
                        "employee_id": emp.employee_id,
                        "employee_name": emp.employee_name,
                        "doc_type": "Passport",
                        "doc_number": emp.passport_number or "N/A",
                        "expiry_date": emp.passport_expiry_date.strftime("%Y-%m-%d"),
                        "days_remaining": days_left,
                        "status": "EXPIRED" if days_left < 0 else ("URGENT" if days_left <= 15 else "WARNING")
                    })
        return alerts
    finally:
        if db is None:
            session.close()


def calculate_saudization_ratio(db: Optional[Session] = None) -> Dict[str, any]:
    """Calculate Nitaqat Saudization percentage and MHRSD band classification"""
    session = SessionLocal() if db is None else db
    try:
        total_emp = session.query(Employee).filter(Employee.is_active == 1).count()
        if total_emp == 0:
            return {
                "total_employees": 0,
                "saudi_count": 0,
                "expat_count": 0,
                "saudization_percentage": 0.0,
                "nitaqat_tier": "Red",
                "badge_color": "red"
            }
        
        saudi_count = session.query(Employee).filter(
            Employee.is_active == 1,
            Employee.nationality_type == "Saudi"
        ).count()
        
        expat_count = total_emp - saudi_count
        ratio = round((saudi_count / total_emp) * 100, 2)
        
        if ratio >= 40.0:
            tier, badge = "Platinum", "green"
        elif ratio >= 30.0:
            tier, badge = "High Green", "lightgreen"
        elif ratio >= 20.0:
            tier, badge = "Mid Green", "yellow"
        elif ratio >= 10.0:
            tier, badge = "Low Green", "orange"
        else:
            tier, badge = "Red", "red"

        return {
            "total_employees": total_emp,
            "saudi_count": saudi_count,
            "expat_count": expat_count,
            "saudization_percentage": ratio,
            "nitaqat_tier": tier,
            "badge_color": badge
        }
    finally:
        if db is None:
            session.close()