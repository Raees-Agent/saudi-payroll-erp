import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json

# 🇸🇦 Page Configuration & Theme Initialization
st.set_page_config(
    page_title="Saudi Enterprise ERP | Payroll & Invoicing Suite",
    page_icon="🇸🇦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import Backend Models & Compliance Logic
from database import SessionLocal, engine, Base, Employee, AttendanceRecord, PayrollRecord, CompanySettings, Customer, Invoice, InvoiceItem, CatalogItem
from payroll import (
    calculate_payroll, process_monthly_payrolls, calculate_gosi_contributions,
    calculate_eosg, generate_sama_wps_sif, get_expiring_documents, calculate_saudization_ratio
)
from invoicing import (
    create_invoice, record_invoice_payment, get_invoicing_kpis, generate_zatca_qr_base64, generate_customer_statement
)
from rag_engine import query_rag_system

# Custom CSS for Corporate High-Contrast Black, Red, and White Theme
st.markdown("""
<style>
    /* Pure Black Main Background & White Typography */
    .stApp {
        background-color: #050505 !important;
        color: #ffffff !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d0d0d !important;
        border-right: 1px solid #262626 !important;
    }
    
    /* Headers & Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    p, label, span, div {
        color: #e5e5e5;
    }

    /* Metric Cards - Black Card with Crimson Red Top Accent Border */
    div[data-testid="stMetric"] {
        background: #121212 !important;
        border: 1px solid #262626 !important;
        border-top: 4px solid #e50914 !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 14px rgba(229, 9, 20, 0.2) !important;
    }
    div[data-testid="stMetric"] label {
        color: #a3a3a3 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }

    /* Primary Buttons - Vivid Crimson Red */
    .stButton button, button[kind="primary"], form button {
        background: linear-gradient(135deg, #e50914 0%, #b91c1c 100%) !important;
        color: #ffffff !important;
        border: 1px solid #dc2626 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 8px rgba(229, 9, 20, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #ff1e27 0%, #dc2626 100%) !important;
        box-shadow: 0 0 15px rgba(229, 9, 20, 0.6) !important;
        transform: translateY(-1px) !important;
    }

    /* Navigation Tabs - Red Highlight */
    div[data-baseweb="tab-highlight"] {
        background-color: #e50914 !important;
    }
    button[data-baseweb="tab"] {
        color: #a3a3a3 !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
    }

    /* Corporate Badges */
    .saudi-badge {
        background: linear-gradient(135deg, #e50914 0%, #991b1b 100%);
        color: #ffffff;
        padding: 8px 18px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
        font-size: 0.9rem;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 10px rgba(229, 9, 20, 0.4);
    }
    .invoice-badge {
        background: linear-gradient(135deg, #dc2626 0%, #7f1d1d 100%);
        color: #ffffff;
        padding: 8px 18px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
        font-size: 0.9rem;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 10px rgba(220, 38, 38, 0.4);
    }

    /* Form Input Fields */
    div[data-baseweb="input"] input, div[data-baseweb="select"] {
        background-color: #141414 !important;
        color: #ffffff !important;
        border-color: #333333 !important;
    }
    div[data-baseweb="input"] input:focus {
        border-color: #e50914 !important;
        box-shadow: 0 0 0 1px #e50914 !important;
    }

    /* Dataframes & Tables */
    .stDataFrame {
        border: 1px solid #262626 !important;
        border-radius: 8px !important;
        background-color: #121212 !important;
    }
</style>
""", unsafe_allow_html=True)

# Session State & Authentication Shield
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'invoice_items_draft' not in st.session_state:
    st.session_state.invoice_items_draft = []

# Security Login Shield
if not st.session_state.authenticated:
    st.title("🔒 Corporate Security Shield | Login Portal")
    st.markdown("### 🇸🇦 Saudi Enterprise ERP Suite (Payroll & Invoicing)")
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("🔑 Commercial Access Gate")
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password", value="8881212")
            submit = st.form_submit_button("Log In to Portal", use_container_width=True)
            
            if submit:
                if username == "admin" and password == "8881212":
                    st.session_state.authenticated = True
                    st.success("Authentication successful!")
                    st.rerun()
                else:
                    st.error("Invalid corporate credentials.")
    st.stop()

# Helper DB Session & Automatic Table Creation
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Ensure default company settings exist in DB
company_info = db.query(CompanySettings).first()
if not company_info:
    company_info = CompanySettings(
        establishment_name="Saudi Corporate Enterprise",
        cr_number="1010000000",
        qiwa_id="7000000000",
        vat_number="310000000000003",
        bank_code="RIBL",
        company_iban="SA0380000000608010167519"
    )
    db.add(company_info)
    db.commit()
    db.refresh(company_info)

# Sidebar Corporate Header & Module Switcher Segment
st.sidebar.markdown("""
<div style="text-align: center; padding: 10px 0;">
    <h2 style="color: #e50914; margin-bottom: 0; font-weight: 800;">🇸🇦 SAUDI ERP</h2>
    <p style="color: #a3a3a3; font-size: 0.85rem;">Enterprise HR & Invoicing Suite</p>
</div>
""", unsafe_allow_html=True)

# SIDEBAR LEFT MODULE SEGMENT SWITCHER
active_module = st.sidebar.radio(
    "📂 SELECT ERP MODULE",
    ["🇸🇦 Saudi Enterprise Payroll & HR", "📜 Corporate Invoicing & Billing", "🧠 AI & RAG Knowledge Assistant"],
    index=0
)

st.sidebar.markdown("---")
company_info = db.query(CompanySettings).first()
if not company_info:
    company_info = CompanySettings()

st.sidebar.markdown(f"**Establishment**: {company_info.establishment_name}")
st.sidebar.markdown(f"**CR Number**: `{company_info.cr_number}`")
st.sidebar.markdown(f"**Qiwa ID**: `{company_info.qiwa_id}`")
st.sidebar.markdown(f"**VAT No**: `{company_info.vat_number}`")
st.sidebar.markdown("---")

if st.sidebar.button("🔒 Log Out", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

# ==============================================================================
# MODULE A: SAUDI ENTERPRISE PAYROLL & HR SUITE
# ==============================================================================
if active_module == "🇸🇦 Saudi Enterprise Payroll & HR":
    
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px;">
        <div>
            <h1 style="margin: 0; color: #ffffff;">🇸🇦 Saudi Enterprise HR & Payroll ERP</h1>
            <p style="color: #a3a3a3; margin: 0;">Fully compliant with MHRSD, GOSI, SAMA WPS (Mudad), and Saudi Labor Law Articles 84 & 85</p>
        </div>
        <div>
            <span class="saudi-badge">MHRSD & SAMA COMPLIANT</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "📊 Executive Dashboard", 
        "💰 Saudi Payroll & WPS", 
        "👤 Employee & Iqama Directory", 
        "⚖️ Saudi EOSG Calculator", 
        "📋 Attendance & Overtime", 
        "🏢 Corporate Settings"
    ])

    # Tab 1: Executive Dashboard
    with t1:
        st.subheader("📊 Executive Overview & Saudization Metrics")
        nitaqat = calculate_saudization_ratio(db)
        doc_alerts = get_expiring_documents(60, db)
        payrolls = db.query(PayrollRecord).all()
        total_gross = sum(p.gross_salary for p in payrolls)
        total_net = sum(p.net_salary for p in payrolls)
        
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Active Workforce", f"{nitaqat['total_employees']} Staff")
        kpi2.metric("Saudization Ratio", f"{nitaqat['saudization_percentage']}%")
        kpi3.metric("Nitaqat Tier", nitaqat['nitaqat_tier'])
        kpi4.metric("Document Alerts", f"{len(doc_alerts)} Alerts")
        kpi5.metric("Total Monthly Net", f"SAR {total_net:,.2f}")
        
        st.markdown("---")
        col_dash1, col_dash2 = st.columns([1.2, 1])
        
        with col_dash1:
            st.markdown("#### 🇸🇦 MHRSD Nitaqat Saudization Status")
            st.progress(min(1.0, nitaqat['saudization_percentage'] / 100.0))
            tier_color = "#e50914" if nitaqat['nitaqat_tier'] in ["Platinum", "High Green"] else ("#dc2626" if "Green" in nitaqat['nitaqat_tier'] else "#991b1b")
            st.markdown(f"""
            <div style="background: #141414; padding: 16px; border-radius: 10px; border-left: 5px solid {tier_color};">
                <h4 style="margin: 0; color: {tier_color};">Current Tier: {nitaqat['nitaqat_tier']}</h4>
                <p style="margin: 5px 0 0 0; color: #a3a3a3;">Saudi Citizens: <b style="color: #ffffff;">{nitaqat['saudi_count']}</b> | Expats: <b style="color: #ffffff;">{nitaqat['expat_count']}</b></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("#### ⚡ Quick Executive Operations")
            qcol1, qcol2 = st.columns(2)
            if qcol1.button("🚀 Process Monthly Payroll Run", use_container_width=True):
                count = process_monthly_payrolls(db)
                st.success(f"Successfully processed payroll for {count} active employees!")
                st.rerun()
                
            if qcol2.button("📥 Generate SAMA WPS SIF File", use_container_width=True):
                sif_res = generate_sama_wps_sif(db=db)
                if sif_res.get("success"):
                    st.download_button(
                        label="💾 Download SIF File",
                        data=sif_res["sif_content"],
                        file_name=sif_res["file_name"],
                        mime="text/plain",
                        use_container_width=True
                    )

        with col_dash2:
            st.markdown("#### ⚠️ Expiring Documents Alert (Iqamas & Passports)")
            if doc_alerts:
                st.dataframe(pd.DataFrame(doc_alerts)[['employee_id', 'employee_name', 'doc_type', 'expiry_date', 'days_remaining', 'status']], use_container_width=True, hide_index=True)
            else:
                st.success("All employee Iqamas and Passports are up to date!")

    # Tab 2: Saudi Payroll & WPS
    with t2:
        st.subheader("💰 Saudi Payroll Management & SAMA WPS SIF Exporter")
        p_tab1, p_tab2, p_tab3 = st.tabs(["⚡ Single Payroll Run", "📊 Monthly Summary Table", "📑 SAMA WPS SIF Export"])
        
        with p_tab1:
            st.markdown("#### Calculate Individual Employee Monthly Payroll")
            employees = db.query(Employee).filter(Employee.is_active == 1).all()
            if employees:
                emp_map = {f"{e.employee_id} - {e.employee_name} ({e.nationality_type})": e.id for e in employees}
                selected_emp_str = st.selectbox("Select Employee", list(emp_map.keys()))
                selected_emp_id = emp_map[selected_emp_str]
                
                if st.button("🧮 Process & Save Payroll", use_container_width=True):
                    res = calculate_payroll(selected_emp_id, db=db)
                    if res.get("success"):
                        st.success(f"Payroll calculated successfully for {res['employee_name']}!")
                        ps1, ps2, ps3 = st.columns(3)
                        with ps1:
                            st.info(f"**Gross Salary**: SAR {res['gross_salary']:,.2f}")
                            st.write(f"- Basic Salary: SAR {res['basic_salary']:,.2f}")
                            st.write(f"- Housing Allowance: SAR {res['housing_allowance']:,.2f}")
                            st.write(f"- Transport Allowance: SAR {res['transport_allowance']:,.2f}")
                            st.write(f"- Overtime Pay: SAR {res['overtime_pay']:,.2f}")
                        with ps2:
                            st.warning(f"**Employee Deductions**: SAR {res['total_deductions']:,.2f}")
                            st.write(f"- GOSI Pension: SAR {res['employee_gosi']:,.2f}")
                            st.write(f"- SANED Unemployment: SAR {res['employee_saned']:,.2f}")
                        with ps3:
                            st.success(f"**NET PAID**: SAR {res['net_salary']:,.2f}")
                            st.write(f"- Employer GOSI/SIF: SAR {res['employer_total_contribution']:,.2f}")
                            st.write(f"- VAT Tally (15%): SAR {res['vat_tally']:,.2f}")
                    else:
                        st.error(res.get("error"))
            else:
                st.info("No active employees registered yet.")
                
        with p_tab2:
            st.markdown("#### Processed Monthly Payroll Records")
            pay_records = db.query(PayrollRecord).all()
            if pay_records:
                pay_data = []
                for p in pay_records:
                    emp = db.query(Employee).filter(Employee.id == p.employee_id).first()
                    pay_data.append({
                        "ID": p.id,
                        "Emp Code": emp.employee_id if emp else "N/A",
                        "Name": emp.employee_name if emp else "N/A",
                        "Nationality": emp.nationality_type if emp else "N/A",
                        "Month": p.month.strftime("%Y-%m") if p.month else "N/A",
                        "Basic Salary": p.basic_salary,
                        "Housing": p.housing_allowance,
                        "Gross Salary": p.gross_salary,
                        "Employee GOSI": p.employee_gosi,
                        "Total Deductions": p.deductions,
                        "NET SALARY (SAR)": p.net_salary,
                        "WPS Status": p.wps_status
                    })
                st.dataframe(pd.DataFrame(pay_data), use_container_width=True, hide_index=True)
            else:
                st.info("No payroll records logged yet.")
                
        with p_tab3:
            st.markdown("#### SAMA & Mudad Wage Protection System (WPS) SIF File Generator")
            sif_month = st.text_input("Payroll Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
            if st.button("⚡ Generate WPS SIF File", key="btn_gen_sif"):
                sif_res = generate_sama_wps_sif(sif_month, db=db)
                if sif_res.get("success"):
                    st.success(f"Generated SIF File: `{sif_res['file_name']}` ({sif_res['record_count']} records, Total: SAR {sif_res['total_salaries_sar']:,.2f})")
                    st.code(sif_res["sif_content"], language="text")
                    st.download_button(label="💾 Download Official .SIF File", data=sif_res["sif_content"], file_name=sif_res["file_name"], mime="text/plain", use_container_width=True)
                else:
                    st.error(sif_res.get("error"))

    # Tab 3: Employee Directory
    with t3:
        st.subheader("👤 Employee Directory & Iqama / Passport Tracking")
        with st.expander("➕ Register New Employee Profile", expanded=False):
            with st.form("add_emp_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    emp_code = st.text_input("Employee Code*", placeholder="e.g. EMP001")
                    first_name = st.text_input("First Name*")
                    last_name = st.text_input("Last Name*")
                    department = st.selectbox("Department", ["General Operations", "Technical Support", "Engineering", "Finance", "Human Resources", "Sales"])
                    position = st.text_input("Position / Job Title", value="Specialist")
                with e_col2:
                    nationality_type = st.selectbox("Nationality Type*", ["Saudi", "Expat"])
                    contract_type = st.selectbox("Contract Type", ["Indefinite", "Fixed"])
                    iqama_id = st.text_input("Iqama ID / National ID*", placeholder="10-digit Saudi ID")
                    passport_number = st.text_input("Passport Number (Expats)")
                    basic_salary = st.number_input("Basic Salary (SAR)*", min_value=0.0, value=5000.0, step=500.0)
                    housing_allowance = st.number_input("Housing Allowance (SAR)", min_value=0.0, value=1250.0, step=250.0)
                    transport_allowance = st.number_input("Transport Allowance (SAR)", min_value=0.0, value=500.0, step=100.0)
                
                b_col1, b_col2 = st.columns(2)
                with b_col1:
                    bank_name = st.text_input("Bank Name", value="Al Rajhi Bank")
                    bank_code = st.text_input("SAMA Bank Code", value="RJHI")
                with b_col2:
                    iban_number = st.text_input("IBAN Number", placeholder="SA0000000000000000000000")
                    
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    iqama_exp = st.date_input("Iqama / ID Expiry Date", value=datetime.now() + timedelta(days=365))
                with d_col2:
                    pass_exp = st.date_input("Passport Expiry Date", value=datetime.now() + timedelta(days=730))
                    
                submit_emp = st.form_submit_button("💾 Save Employee Profile", use_container_width=True)
                if submit_emp and emp_code and first_name and last_name:
                    new_emp = Employee(
                        employee_id=emp_code, first_name=first_name, last_name=last_name,
                        department=department, position=position, nationality_type=nationality_type,
                        contract_type=contract_type, iqama_id=iqama_id, passport_number=passport_number,
                        basic_salary=basic_salary, housing_allowance=housing_allowance, transport_allowance=transport_allowance,
                        base_salary=basic_salary + housing_allowance + transport_allowance, hourly_rate=basic_salary / 208.0,
                        bank_name=bank_name, bank_code=bank_code, iban_number=iban_number,
                        iqama_expiry_date=datetime.combine(iqama_exp, datetime.min.time()),
                        passport_expiry_date=datetime.combine(pass_exp, datetime.min.time()), is_active=1
                    )
                    db.add(new_emp)
                    db.commit()
                    st.success("Employee registered successfully!")
                    st.rerun()
                    
        employees = db.query(Employee).filter(Employee.is_active == 1).all()
        if employees:
            st.dataframe(pd.DataFrame([{
                "ID": e.id, "Emp Code": e.employee_id, "Name": e.employee_name, "Nationality": e.nationality_type,
                "Department": e.department, "Iqama / Nat ID": e.iqama_id or "N/A", "Basic Salary": f"SAR {e.basic_salary or e.base_salary:,.2f}",
                "Iqama Expiry": e.iqama_expiry_date.strftime("%Y-%m-%d") if e.iqama_expiry_date else "N/A"
            } for e in employees]), use_container_width=True, hide_index=True)

    # Tab 4: EOSG Calculator
    with t4:
        st.subheader("⚖️ Saudi Labor Law End-of-Service (EOSG) Calculator")
        col_eosg1, col_eosg2 = st.columns(2)
        with col_eosg1:
            eosg_basic = st.number_input("Monthly Basic Salary (SAR)", min_value=0.0, value=6000.0, step=500.0)
            eosg_housing = st.number_input("Monthly Housing Allowance (SAR)", min_value=0.0, value=1500.0, step=250.0)
            eosg_transport = st.number_input("Monthly Transport Allowance (SAR)", min_value=0.0, value=500.0, step=100.0)
            eosg_other = st.number_input("Other Fixed Allowances (SAR)", min_value=0.0, value=0.0, step=100.0)
        with col_eosg2:
            eosg_years = st.number_input("Tenure / Continuous Service (Years)", min_value=0.1, value=3.5, step=0.5)
            eosg_reason = st.selectbox("Separation Reason", ["Resignation by Employee", "Termination by Employer (Article 84)", "End of Fixed-Term Contract", "Force Majeure"])
            eosg_contract = st.selectbox("Contract Type", ["Indefinite", "Fixed"])

        eosg_res = calculate_eosg(eosg_basic, eosg_housing, eosg_transport, eosg_other, eosg_years, eosg_reason, eosg_contract)
        st.success(f"### 💰 PROPOSED LIQUID EOSG PAYOUT: SAR {eosg_res['final_eosg_payout']:,.2f}")
        st.caption(f"**Legal Clause applied**: {eosg_res['clause']}")

    # Tab 5: Attendance
    with t5:
        st.subheader("📋 Workforce Attendance Punch Logs & 1.5x Overtime Engine")
        employees = db.query(Employee).filter(Employee.is_active == 1).all()
        if employees:
            with st.form("att_form"):
                emp_map_att = {f"{e.employee_id} - {e.employee_name}": e.id for e in employees}
                att_emp_str = st.selectbox("Select Employee", list(emp_map_att.keys()))
                hours_worked = st.number_input("Total Hours Worked", min_value=0.0, value=9.5, step=0.5)
                att_submit = st.form_submit_button("💾 Record Punch Entry", use_container_width=True)
                if att_submit:
                    emp_id = emp_map_att[att_emp_str]
                    new_att = AttendanceRecord(employee_id=emp_id, date=datetime.now(), hours_worked=hours_worked, overtime_hours=max(0.0, hours_worked - 8.0), attendance_status="Regular")
                    db.add(new_att)
                    db.commit()
                    st.success("Attendance punch recorded!")
                    st.rerun()

    # Tab 6: Corporate Settings
    with t6:
        st.subheader("🏢 Establishment & Corporate Compliance Settings")
        with st.form("company_settings_form"):
            c1, c2 = st.columns(2)
            with c1:
                est_name = st.text_input("Establishment Legal Name", value=company_info.establishment_name)
                cr_num = st.text_input("Commercial Registration (CR) Number", value=company_info.cr_number)
                qiwa_num = st.text_input("Qiwa / MOL Establishment ID", value=company_info.qiwa_id)
            with c2:
                vat_num = st.text_input("VAT Registration Number (15 digits)", value=company_info.vat_number)
                bank_code_str = st.text_input("SAMA Primary Bank Code", value=company_info.bank_code)
                company_iban_str = st.text_input("Corporate IBAN Account Number", value=company_info.company_iban or "SA0000000000000000000000")
            submit_comp = st.form_submit_button("💾 Save Settings", use_container_width=True)
            if submit_comp:
                company_info.establishment_name = est_name
                company_info.cr_number = cr_num
                company_info.qiwa_id = qiwa_num
                company_info.vat_number = vat_num
                company_info.bank_code = bank_code_str
                company_info.company_iban = company_iban_str
                db.commit()
                st.success("Settings saved successfully!")
                st.rerun()

# ==============================================================================
# MODULE B: CORPORATE INVOICING & BILLING SUITE
# ==============================================================================
elif active_module == "📜 Corporate Invoicing & Billing":
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px;">
        <div>
            <h1 style="margin: 0; color: #ffffff;">📜 Corporate Invoicing & Billing Suite</h1>
            <p style="color: #8b949e; margin: 0;">Enterprise E-Invoicing & Billing Engine (15% VAT & QR Code Support)</p>
        </div>
        <div>
            <span class="invoice-badge">INVOICING SYSTEM</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    inv_t1, inv_t2, inv_t3, inv_t4, inv_t5, inv_t6 = st.tabs([
        "📊 Billing Dashboard", 
        "➕ Create Tax Invoice", 
        "📄 Invoice Manager & Printable View", 
        "📑 Statement of Account (SOA)",
        "👥 Client & Customer Directory", 
        "📦 Products & Catalog"
    ])

    # Tab B1: Billing Dashboard
    with inv_t1:
        st.subheader("📊 Corporate Billing & Receivables Dashboard")
        kpis = get_invoicing_kpis(db)
        
        ikpi1, ikpi2, ikpi3, ikpi4 = st.columns(4)
        ikpi1.metric("Total Invoices Issued", f"{kpis['total_invoices_count']} Invoices")
        ikpi2.metric("Total Billed Revenue", f"SAR {kpis['total_invoiced_sar']:,.2f}")
        ikpi3.metric("Total Collections", f"SAR {kpis['total_paid_sar']:,.2f}")
        ikpi4.metric("Outstanding Receivables", f"SAR {kpis['outstanding_receivables_sar']:,.2f}")
        
        st.markdown("---")
        
        st.markdown("#### 📜 Recent Corporate Invoices")
        recent_invoices = db.query(Invoice).order_by(Invoice.issue_date.desc()).limit(10).all()
        if recent_invoices:
            inv_data = []
            for i in recent_invoices:
                cust = db.query(Customer).filter(Customer.id == i.customer_id).first()
                inv_data.append({
                    "Invoice #": i.invoice_number,
                    "Type": i.invoice_type,
                    "Client": cust.customer_name if cust else "N/A",
                    "Issue Date": i.issue_date.strftime("%Y-%m-%d") if i.issue_date else "N/A",
                    "Subtotal": f"SAR {i.subtotal:,.2f}",
                    "VAT (15%)": f"SAR {i.vat_total:,.2f}",
                    "TOTAL AMOUNT": f"SAR {i.total_amount:,.2f}",
                    "Status": i.status
                })
            st.dataframe(pd.DataFrame(inv_data), use_container_width=True, hide_index=True)
        else:
            st.info("No invoices generated yet. Use 'Create Tax Invoice' tab to issue an invoice.")

    # Tab B2: Create Invoice
    with inv_t2:
        st.subheader("➕ Create Tax Invoice (Client, Services, Govt Fee, VAT & Service Charges)")
        
        customers = db.query(Customer).filter(Customer.is_active == 1).all()
        if not customers:
            st.warning("Please register at least one Customer in the 'Client & Customer Directory' tab first.")
        else:
            c_map = {f"{c.customer_name} (VAT: {c.vat_number or 'N/A'})": c.id for c in customers}
            sel_cust_str = st.selectbox("Select Client / Buyer Name*", list(c_map.keys()))
            sel_cust_id = c_map[sel_cust_str]
            
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                inv_type = st.selectbox("Invoice Type", ["Tax Invoice", "Simplified Tax Invoice"])
                inv_due = st.date_input("Due Date", value=datetime.now() + timedelta(days=30))
            with c_col2:
                inv_notes = st.text_input("Payment Terms / Notes", value="Payment due within 30 days via bank transfer")

            st.markdown("---")
            st.markdown("#### 📦 Add Services & Fee Breakdown Item")
            
            # Catalog Item Selector
            catalog = db.query(CatalogItem).filter(CatalogItem.is_active == 1).all()
            if catalog:
                cat_map = {f"{cat.item_name} - SAR {cat.unit_price:,.2f}": cat for cat in catalog}
                sel_cat_str = st.selectbox("Select item from Catalog (optional fast add)", ["-- Custom Line Item --"] + list(cat_map.keys()))
            else:
                sel_cat_str = "-- Custom Line Item --"
            
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                desc_val = "" if sel_cat_str == "-- Custom Line Item --" else cat_map[sel_cat_str].description or cat_map[sel_cat_str].item_name
                desc_input = st.text_input("Service / Task Description*", value=desc_val, placeholder="e.g. Iqama Renewal / Commercial License")
            with f_col2:
                ben_input = st.text_input("Beneficiary Name / Employee Name", placeholder="e.g. John Doe (Iqama # 2400112233)")

            g_col1, g_col2, g_col3 = st.columns(3)
            with g_col1:
                qty_input = st.number_input("Quantity*", min_value=1.0, value=1.0, step=1.0)
            with g_col2:
                govt_fee_input = st.number_input("Govt Fee (SAR)", min_value=0.0, value=0.0, step=50.0)
            with g_col3:
                price_val = 0.0 if sel_cat_str == "-- Custom Line Item --" else cat_map[sel_cat_str].unit_price
                service_charge_input = st.number_input("Service Charge (SAR)", min_value=0.0, value=price_val, step=50.0)

            vat_preview = round(service_charge_input * qty_input * 0.15, 2)
            line_tot_preview = round((govt_fee_input * qty_input) + (service_charge_input * qty_input) + vat_preview, 2)
            st.caption(f"💡 Line Breakdown: Govt Fee: **SAR {govt_fee_input * qty_input:,.2f}** | Service Charge: **SAR {service_charge_input * qty_input:,.2f}** | VAT (15% on Service Charge): **SAR {vat_preview:,.2f}** ➡️ Total Line: **SAR {line_tot_preview:,.2f}**")

            if st.button("➕ Add Service Line Item", key="btn_add_item"):
                if desc_input and (govt_fee_input > 0 or service_charge_input > 0):
                    st.session_state.invoice_items_draft.append({
                        "description": desc_input,
                        "beneficiary_name": ben_input,
                        "quantity": qty_input,
                        "govt_fee": govt_fee_input,
                        "service_charge": service_charge_input,
                        "vat_rate": 0.15
                    })
                    st.success(f"Added service line: '{desc_input}' for '{ben_input or 'N/A'}'")
                    st.rerun()
                else:
                    st.error("Please enter a valid Service Description and either a Govt Fee or Service Charge amount.")

            # Draft Line Items Table
            if st.session_state.invoice_items_draft:
                st.markdown("##### Current Invoice Draft Line Items:")
                draft_data = []
                g_fee_sum = 0.0
                s_charge_sum = 0.0
                vat_sum = 0.0
                for idx, it in enumerate(st.session_state.invoice_items_draft):
                    q = it['quantity']
                    g = round(it.get('govt_fee', 0.0) * q, 2)
                    s = round(it.get('service_charge', 0.0) * q, 2)
                    v_amt = round(s * 0.15, 2)
                    tot = round(g + s + v_amt, 2)
                    g_fee_sum += g
                    s_charge_sum += s
                    vat_sum += v_amt
                    draft_data.append({
                        "#": idx + 1,
                        "Service Description": it['description'],
                        "Beneficiary Name": it.get('beneficiary_name') or "N/A",
                        "Qty": q,
                        "Govt Fee (SAR)": f"SAR {g:,.2f}",
                        "Service Charge (SAR)": f"SAR {s:,.2f}",
                        "VAT 15% (SAR)": f"SAR {v_amt:,.2f}",
                        "Line Total (SAR)": f"SAR {tot:,.2f}"
                    })
                st.dataframe(pd.DataFrame(draft_data), use_container_width=True, hide_index=True)
                
                sub_sum = g_fee_sum + s_charge_sum
                tot_net_sum = sub_sum + vat_sum
                
                st.markdown("##### Invoice Financial Breakdown")
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.info(f"**Total Govt Fees**: SAR {g_fee_sum:,.2f}")
                sc2.info(f"**Total Service Charges**: SAR {s_charge_sum:,.2f}")
                sc3.warning(f"**VAT 15% (on Services)**: SAR {vat_sum:,.2f}")
                sc4.success(f"**GRAND NET TOTAL**: SAR {tot_net_sum:,.2f}")

                # Live QR Code Preview
                company = db.query(CompanySettings).first() or CompanySettings()
                qr_base64 = generate_zatca_qr_base64(
                    seller_name=company.establishment_name,
                    vat_number=company.vat_number,
                    timestamp_str=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    total_amount=tot_net_sum,
                    vat_amount=vat_sum
                )
                st.caption(f"**Base64 TLV QR Code Hash**: `{qr_base64[:60]}...`")

                btn_col1, btn_col2 = st.columns(2)
                if btn_col1.button("🚀 Issue Tax Invoice", use_container_width=True):
                    inv_data = {
                        "customer_id": sel_cust_id,
                        "invoice_type": inv_type,
                        "due_date": datetime.combine(inv_due, datetime.min.time()).isoformat(),
                        "notes": inv_notes,
                        "status": "Issued"
                    }
                    res = create_invoice(inv_data, st.session_state.invoice_items_draft, db=db)
                    if res.get("success"):
                        st.session_state.invoice_items_draft = []
                        st.success(f"Invoice `{res['invoice_number']}` created successfully!")
                        st.rerun()
                    else:
                        st.error(res.get("error"))
                        
                if btn_col2.button("🗑️ Clear Draft Items", use_container_width=True):
                    st.session_state.invoice_items_draft = []
                    st.rerun()

    # Tab B3: Invoice Manager & Printable View
    with inv_t3:
        st.subheader("📄 Invoice Manager & Printable Tax Invoices")
        invoices = db.query(Invoice).order_by(Invoice.issue_date.desc()).all()
        if invoices:
            inv_select_map = {f"{i.invoice_number} - {i.status} (SAR {i.total_amount:,.2f})": i.id for i in invoices}
            sel_inv_str = st.selectbox("Select Invoice to View / Manage", list(inv_select_map.keys()))
            sel_inv_id = inv_select_map[sel_inv_str]
            
            target_inv = db.query(Invoice).filter(Invoice.id == sel_inv_id).first()
            cust = db.query(Customer).filter(Customer.id == target_inv.customer_id).first()
            items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == target_inv.id).all()
            company = db.query(CompanySettings).first() or CompanySettings()

            st.markdown("---")
            # Printable Tax Invoice Template Container
            st.markdown(f"""
            <div style="background: #141414; border: 2px solid #e50914; border-radius: 12px; padding: 24px; box-shadow: 0 4px 15px rgba(229, 9, 20, 0.2);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #e50914; padding-bottom: 15px; margin-bottom: 20px;">
                    <div>
                        <h2 style="color: #e50914; margin: 0; font-weight: 800;">{company.establishment_name}</h2>
                        <p style="color: #a3a3a3; margin: 2px 0;">CR: {company.cr_number} | VAT ID: {company.vat_number}</p>
                        <p style="color: #a3a3a3; margin: 0;">IBAN: {company.company_iban or 'N/A'}</p>
                    </div>
                    <div style="text-align: right;">
                        <h2 style="color: #ffffff; margin: 0; font-weight: 800;">{target_inv.invoice_type.upper()}</h2>
                        <p style="color: #ffffff; font-size: 1.1rem; font-weight: bold; margin: 2px 0;">{target_inv.invoice_number}</p>
                        <p style="color: #a3a3a3; margin: 0;">Status: <b style="color: #e50914;">{target_inv.status}</b></p>
                    </div>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                    <div style="width: 48%;">
                        <h4 style="color: #8b949e; margin-bottom: 5px;">CLIENT / BUYER NAME:</h4>
                        <p style="margin: 0; font-size: 1.05rem;"><b>{cust.customer_name if cust else 'N/A'}</b></p>
                        <p style="margin: 0; color: #8b949e;">VAT No: {cust.vat_number if cust else 'N/A'}</p>
                        <p style="margin: 0; color: #8b949e;">Address: {cust.address if cust else 'Riyadh, Saudi Arabia'}</p>
                    </div>
                    <div style="width: 48%; text-align: right;">
                        <h4 style="color: #8b949e; margin-bottom: 5px;">INVOICE DATES:</h4>
                        <p style="margin: 0; color: #8b949e;">Issue Date: <b>{target_inv.issue_date.strftime('%Y-%m-%d %H:%M') if target_inv.issue_date else 'N/A'}</b></p>
                        <p style="margin: 0; color: #8b949e;">Due Date: <b>{target_inv.due_date.strftime('%Y-%m-%d') if target_inv.due_date else 'N/A'}</b></p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("#### Itemized Services & Fee Breakdown:")
            st.dataframe(pd.DataFrame([{
                "Service Description": it.description,
                "Beneficiary Name": it.beneficiary_name or "N/A",
                "Qty": it.quantity,
                "Govt Fee (SAR)": f"SAR {it.govt_fee or 0.0:,.2f}",
                "Service Charge (SAR)": f"SAR {it.service_charge or 0.0:,.2f}",
                "VAT 15% (SAR)": f"SAR {it.vat_amount:,.2f}",
                "Line Total (SAR)": f"SAR {it.total_amount:,.2f}"
            } for it in items]), use_container_width=True, hide_index=True)

            st.markdown("#### Invoice Financial Totals & QR Code:")
            inv_col1, inv_col2 = st.columns([1, 1])
            with inv_col1:
                st.code(f"Base64 TLV QR Code:\n{target_inv.zatca_qr_code or 'N/A'}", language="text")
            with inv_col2:
                st.info(f"**Subtotal**: SAR {target_inv.subtotal:,.2f}")
                st.warning(f"**15% VAT Total**: SAR {target_inv.vat_total:,.2f}")
                st.success(f"**NET TOTAL**: SAR {target_inv.total_amount:,.2f}")
                st.write(f"Paid Amount: SAR {target_inv.paid_amount or 0.0:,.2f}")

            st.markdown("---")
            st.markdown("#### 💳 Record Payment against Invoice")
            p_col1, p_col2 = st.columns([2, 1])
            with p_col1:
                pay_amt = st.number_input("Payment Amount Received (SAR)", min_value=0.1, value=max(0.1, target_inv.total_amount - (target_inv.paid_amount or 0.0)))
            with p_col2:
                if st.button("💾 Record Payment", use_container_width=True):
                    pres = record_invoice_payment(target_inv.id, pay_amt, db=db)
                    if pres.get("success"):
                        st.success(f"Payment recorded! New status: `{pres['status']}`")
                        st.rerun()

    # Tab B4: Statement of Account (SOA)
    with inv_t4:
        st.subheader("📑 Statement of Account (SOA)")
        st.info("Generate official client ledger statement showing all billed invoices, payments received, and running balance due.")
        
        customers = db.query(Customer).filter(Customer.is_active == 1).all()
        if customers:
            soa_cust_map = {f"{c.customer_name} (VAT: {c.vat_number or 'N/A'})": c.id for c in customers}
            sel_soa_cust = st.selectbox("Select Target Client / Customer*", list(soa_cust_map.keys()))
            soa_cust_id = soa_cust_map[sel_soa_cust]
            
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                soa_start = st.date_input("Start Date (optional)", value=datetime.now() - timedelta(days=90))
            with s_col2:
                soa_end = st.date_input("End Date (optional)", value=datetime.now())
                
            soa_res = generate_customer_statement(
                customer_id=soa_cust_id,
                start_date=datetime.combine(soa_start, datetime.min.time()).isoformat(),
                end_date=datetime.combine(soa_end, datetime.max.time()).isoformat(),
                db=db
            )
            
            if soa_res.get("success"):
                summ = soa_res["statement_summary"]
                cust_info = soa_res["customer"]
                seller_info = soa_res["seller"]
                
                st.markdown("---")
                # Printable Statement of Account Container
                st.markdown(f"""
                <div style="background: #141414; border: 2px solid #e50914; border-radius: 12px; padding: 24px; box-shadow: 0 4px 15px rgba(229, 9, 20, 0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #e50914; padding-bottom: 15px; margin-bottom: 20px;">
                        <div>
                            <h2 style="color: #e50914; margin: 0; font-weight: 800;">{seller_info['name']}</h2>
                            <p style="color: #a3a3a3; margin: 2px 0;">CR: {seller_info['cr_number']} | VAT ID: {seller_info['vat_number']}</p>
                            <p style="color: #a3a3a3; margin: 0;">IBAN: {seller_info['iban'] or 'N/A'}</p>
                        </div>
                        <div style="text-align: right;">
                            <h2 style="color: #ffffff; margin: 0; font-weight: 800;">STATEMENT OF ACCOUNT</h2>
                            <p style="color: #a3a3a3; margin: 2px 0;">Statement Date: <b style="color: #ffffff;">{summ['statement_date']}</b></p>
                        </div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <div>
                            <h4 style="color: #8b949e; margin-bottom: 5px;">CLIENT / ACCOUNT NAME:</h4>
                            <p style="margin: 0; font-size: 1.1rem; color: #ffffff;"><b>{cust_info['name']}</b></p>
                            <p style="margin: 0; color: #a3a3a3;">VAT ID: {cust_info['vat_number'] or 'N/A'} | CR: {cust_info['cr_number'] or 'N/A'}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("##### Statement Financial Summary")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Invoiced Revenue", f"SAR {summ['total_billed_sar']:,.2f}")
                m2.metric("Total Payments Received", f"SAR {summ['total_paid_sar']:,.2f}")
                m3.metric("CURRENT BALANCE DUE", f"SAR {summ['outstanding_balance_sar']:,.2f}")
                
                st.markdown("##### Detailed Ledger Transactions History:")
                if soa_res["ledger_entries"]:
                    df_ledger = pd.DataFrame(soa_res["ledger_entries"])
                    df_ledger.columns = ["Date", "Reference #", "Type", "Billed Amount (SAR)", "Paid Amount (SAR)", "Running Balance (SAR)", "Status"]
                    
                    st.dataframe(df_ledger, use_container_width=True, hide_index=True)
                    
                    # CSV Export
                    csv_data = df_ledger.to_csv(index=False)
                    st.download_button(
                        label="📥 Export Statement of Account (CSV)",
                        data=csv_data,
                        file_name=f"SOA_{cust_info['name'].replace(' ', '_')}_{summ['statement_date']}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No transaction ledger entries found for this client in the selected date range.")
        else:
            st.info("No active B2B Customers found. Add a customer profile first.")

    # Tab B5: Client & Customer Directory
    with inv_t5:
        st.subheader("👥 Client & B2B Customer Directory")
        
        c_tab1, c_tab2 = st.tabs(["➕ Register New Client", "✏️ Edit / Update Client Profile"])
        
        with c_tab1:
            with st.form("add_cust_form"):
                cust_col1, cust_col2 = st.columns(2)
                with cust_col1:
                    c_name = st.text_input("Customer / Company Name*")
                    c_vat = st.text_input("15-digit VAT ID*", placeholder="310000000000003")
                    c_cr = st.text_input("CR Number", placeholder="1010000000")
                with cust_col2:
                    c_email = st.text_input("Billing Email")
                    c_phone = st.text_input("Phone Number")
                    c_address = st.text_input("Street Address", value="King Fahd Road")
                    c_city = st.text_input("City", value="Riyadh")
                    
                sub_cust = st.form_submit_button("💾 Save Customer Profile", use_container_width=True)
                if sub_cust and c_name:
                    new_c = Customer(customer_name=c_name, vat_number=c_vat, cr_number=c_cr, email=c_email, phone=c_phone, address=c_address, city=c_city)
                    db.add(new_c)
                    db.commit()
                    st.success(f"Customer '{c_name}' registered successfully! Appears in Invoice section instantly.")
                    st.rerun()

        all_cust = db.query(Customer).filter(Customer.is_active == 1).all()
        
        with c_tab2:
            if all_cust:
                edit_cust_map = {f"{c.customer_name} (ID: {c.id})": c for c in all_cust}
                sel_edit_str = st.selectbox("Select Client Profile to Edit*", list(edit_cust_map.keys()))
                target_c = edit_cust_map[sel_edit_str]
                
                with st.form("edit_cust_form"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_name = st.text_input("Customer Name*", value=target_c.customer_name)
                        e_vat = st.text_input("VAT ID*", value=target_c.vat_number or "")
                        e_cr = st.text_input("CR Number", value=target_c.cr_number or "")
                    with ec2:
                        e_email = st.text_input("Billing Email", value=target_c.email or "")
                        e_phone = st.text_input("Phone Number", value=target_c.phone or "")
                        e_address = st.text_input("Address", value=target_c.address or "")
                        e_city = st.text_input("City", value=target_c.city or "Riyadh")
                        
                    btn_save_edit = st.form_submit_button("💾 Save Changes to Client Profile", use_container_width=True)
                    if btn_save_edit and e_name:
                        target_c.customer_name = e_name
                        target_c.vat_number = e_vat
                        target_c.cr_number = e_cr
                        target_c.email = e_email
                        target_c.phone = e_phone
                        target_c.address = e_address
                        target_c.city = e_city
                        db.commit()
                        st.success(f"Client profile '{e_name}' updated! All invoice dropdowns & printable view reflect these changes in real-time.")
                        st.rerun()
            else:
                st.info("No client profiles available to edit.")

        st.markdown("---")
        st.markdown("##### Active B2B Client Profiles Directory:")
        if all_cust:
            st.dataframe(pd.DataFrame([{
                "ID": c.id,
                "Company Name": c.customer_name,
                "VAT Number": c.vat_number or "N/A",
                "CR Number": c.cr_number or "N/A",
                "Email": c.email or "N/A",
                "Phone": c.phone or "N/A",
                "City": c.city
            } for c in all_cust]), use_container_width=True, hide_index=True)
        else:
            st.info("No active B2B Client Profiles found. Use the form above to add a client.")

    # Tab B6: Products & Catalog
    with inv_t6:
        st.subheader("📦 Services & Products Item Catalog")
        
        with st.expander("➕ Add Item to Preset Catalog", expanded=False):
            with st.form("add_cat_form"):
                cat_name = st.text_input("Item / Service Name*")
                cat_desc = st.text_input("Description")
                cat_price = st.number_input("Unit Price (SAR)*", min_value=0.0, value=1000.0, step=100.0)
                cat_type = st.selectbox("Category", ["Services", "Consulting", "Software", "Hardware", "Maintenance"])
                
                sub_cat = st.form_submit_button("💾 Save Catalog Item", use_container_width=True)
                if sub_cat and cat_name:
                    new_item = CatalogItem(item_name=cat_name, description=cat_desc, unit_price=cat_price, category=cat_type)
                    db.add(new_item)
                    db.commit()
                    st.success("Catalog item added successfully!")
                    st.rerun()
                    
        cat_items = db.query(CatalogItem).filter(CatalogItem.is_active == 1).all()
        if cat_items:
            st.dataframe(pd.DataFrame([{
                "ID": ci.id,
                "Item Name": ci.item_name,
                "Category": ci.category,
                "Unit Price (SAR)": f"SAR {ci.unit_price:,.2f}",
                "Description": ci.description or "N/A"
            } for ci in cat_items]), use_container_width=True, hide_index=True)

# ==============================================================================
# MODULE C: AI & RAG KNOWLEDGE ASSISTANT
# ==============================================================================
elif active_module == "🧠 AI & RAG Knowledge Assistant":
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px;">
        <div>
            <h1 style="margin: 0; color: #ffffff;">🧠 AI & RAG Knowledge Assistant</h1>
            <p style="color: #a3a3a3; margin: 0;">Retrieval-Augmented Generation across Saudi Labor Laws, GOSI, MHRSD, 15% VAT, and Real-time ERP Database Records</p>
        </div>
        <div>
            <span class="saudi-badge">AI RAG ENGINE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    rag_query = st.text_input("🔍 Search Knowledge Base or Query ERP Records...", placeholder="e.g. Article 84 EOSG formula, or search client name, invoice number, GOSI rates")

    st.markdown("#### ⚡ Preset Quick RAG Queries")
    q1, q2, q3, q4 = st.columns(4)
    if q1.button("⚖️ EOSG Article 84/85"):
        rag_query = "Article 84 & 85 End-of-Service Gratuity (EOSG)"
    if q2.button("💰 GOSI & SANED Rates"):
        rag_query = "GOSI Social Insurance Rates Saudi vs Expat"
    if q3.button("📜 15% VAT & TLV QR Code"):
        rag_query = "Tax Invoice & Base64 TLV QR Code"
    if q4.button("👥 Search Active Clients"):
        rag_query = "Search Active Clients and Invoices"

    if rag_query:
        st.markdown("---")
        rag_res = query_rag_system(rag_query, db=db)
        
        st.subheader(f"🧠 RAG Analysis for: '{rag_query}'")
        st.caption(f"**Timestamp**: `{rag_res['timestamp']}` | **Retrieved Knowledge Snippets**: `{rag_res['retrieved_knowledge_count']}`")
        
        st.markdown(f"""
        <div style="background: #141414; border: 2px solid #e50914; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(229, 9, 20, 0.2);">
            <pre style="color: #ffffff; white-space: pre-wrap; font-family: inherit; font-size: 1rem;">{rag_res['synthesized_response']}</pre>
        </div>
        """, unsafe_allow_html=True)

db.close()
