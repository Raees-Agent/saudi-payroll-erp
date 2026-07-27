#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) Engine for Saudi Enterprise ERP.
Retrieves context from Saudi Labor Laws, GOSI Rules, MHRSD Compliance, and real-time ERP Database records.
"""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database import Employee, Customer, Invoice, InvoiceItem, CompanySettings, CatalogItem

# Built-in Knowledge Base Knowledge Documents
SAUDI_KNOWLEDGE_BASE = [
    {
        "category": "Saudi Labor Law - EOSG",
        "title": "Article 84 & 85 End-of-Service Gratuity (EOSG)",
        "content": (
            "Under Article 84 of the Saudi Labor Law, upon termination of the employment contract by the employer, "
            "the employee is entitled to EOSG calculated as: Half a month's wage for each of the first 5 years of service, "
            "and a full month's wage for each subsequent year. "
            "Under Article 85, if an employee resigns: Service under 2 years receives 0 payout; Service 2 to 5 years receives 1/3 of EOSG; "
            "Service 5 to 10 years receives 2/3 of EOSG; Service over 10 years receives 100% full EOSG payout. "
            "EOSG wage base includes Basic Salary + Housing Allowance + Transport Allowance + Fixed Allowances."
        )
    },
    {
        "category": "GOSI & SANED Regulations",
        "title": "GOSI Social Insurance Rates",
        "content": (
            "GOSI social insurance contributions in Saudi Arabia: "
            "For Saudi National Employees: Employee pays 9.75% (9% Annuities + 0.75% SANED Unemployment), "
            "Employer pays 11.75% (9% Annuities + 0.75% SANED + 2% Occupational Hazards). "
            "GOSI contribution wage is capped at SAR 45,000 per month (Basic + Housing). "
            "For Expat Employees: Employee pays 0%, Employer pays 2% Occupational Hazards contribution."
        )
    },
    {
        "category": "MHRSD Nitaqat Compliance",
        "title": "Nitaqat Saudization Categories & Ratings",
        "content": (
            "MHRSD Nitaqat program measures the percentage of Saudi citizens employed in an establishment. "
            "Establishments are categorized into 5 tiers: Platinum, High Green, Mid Green, Low Green, and Red. "
            "Red tier establishments are blocked from issuing new expat visas, transferring employee sponsorships, or renewing Iqamas. "
            "Higher Saudization tiers unlock expedited MHRSD services and Qiwa portal privileges."
        )
    },
    {
        "category": "SAMA & Mudad WPS",
        "title": "Wage Protection System (WPS) & SIF Files",
        "content": (
            "SAMA and MHRSD mandate all private sector establishments in Saudi Arabia to disburse monthly salaries via WPS. "
            "Salary Files (.sif) must follow SAMA specifications containing Header (01), Salary Detail (02), and Control (03) records. "
            "Salaries must be paid in Saudi Riyals (SAR) to valid Saudi IBAN accounts by the 10th of every month to avoid Qiwa blocking."
        )
    },
    {
        "category": "Corporate Invoicing & 15% VAT",
        "title": "Tax Invoice & Base64 TLV QR Code",
        "content": (
            "Corporate Invoicing in Saudi Arabia mandates 15% VAT on taxable goods and professional service charges. "
            "Tax Invoices must display Seller Establishment Name, 15-digit VAT Registration Number, CR Number, "
            "Buyer/Client Name & VAT Number, Itemized line subtotals, VAT amount, and a Base64 encoded TLV QR Code. "
            "The TLV QR Code encodes: Tag 1 (Seller Name), Tag 2 (VAT Number), Tag 3 (Timestamp), Tag 4 (Invoice Total), Tag 5 (VAT Total)."
        )
    }
]


def search_knowledge_base(query: str) -> List[Dict[str, str]]:
    """Search internal legal and regulatory knowledge base using keyword matching."""
    query_words = [w.lower() for w in query.split() if len(w) > 2]
    matched_docs = []
    
    for doc in SAUDI_KNOWLEDGE_BASE:
        text = (doc["title"] + " " + doc["category"] + " " + doc["content"]).lower()
        score = sum(1 for w in query_words if w in text)
        if score > 0 or not query_words:
            matched_docs.append((score, doc))
            
    matched_docs.sort(key=lambda x: x[0], reverse=True)
    return [doc for score, doc in matched_docs[:3]]


def search_erp_database(query: str, db: Session) -> Dict[str, any]:
    """Retrieve relevant real-time records from SQLite database matching query."""
    q_clean = query.lower().strip()
    res = {
        "customers": [],
        "invoices": [],
        "employees": [],
        "catalog_items": []
    }
    
    if not db:
        return res

    # 1. Customers
    custs = db.query(Customer).filter(Customer.is_active == 1).all()
    for c in custs:
        if q_clean in c.customer_name.lower() or (c.vat_number and q_clean in c.vat_number) or (c.cr_number and q_clean in c.cr_number):
            res["customers"].append({
                "id": c.id,
                "name": c.customer_name,
                "vat_number": c.vat_number,
                "cr_number": c.cr_number,
                "city": c.city
            })

    # 2. Invoices
    invs = db.query(Invoice).filter(Invoice.status != "Cancelled").all()
    for i in invs:
        if q_clean in i.invoice_number.lower() or q_clean in i.status.lower():
            cust = db.query(Customer).filter(Customer.id == i.customer_id).first()
            res["invoices"].append({
                "invoice_number": i.invoice_number,
                "client": cust.customer_name if cust else "N/A",
                "total_amount": i.total_amount,
                "paid_amount": i.paid_amount,
                "status": i.status
            })

    # 3. Employees
    emps = db.query(Employee).filter(Employee.is_active == 1).all()
    for e in emps:
        if q_clean in e.employee_name.lower() or q_clean in e.employee_id.lower() or (e.iqama_id and q_clean in e.iqama_id):
            res["employees"].append({
                "emp_id": e.employee_id,
                "name": e.employee_name,
                "nationality": e.nationality_type,
                "department": e.department
            })

    # 4. Catalog Items
    cats = db.query(CatalogItem).filter(CatalogItem.is_active == 1).all()
    for ci in cats:
        if q_clean in ci.item_name.lower() or (ci.category and q_clean in ci.category.lower()):
            res["catalog_items"].append({
                "item_name": ci.item_name,
                "unit_price": ci.unit_price,
                "category": ci.category
            })

    return res


def query_rag_system(user_query: str, db: Optional[Session] = None) -> Dict[str, any]:
    """
    RAG Pipeline: Retrieves relevant legal docs + ERP live DB context and synthesizes response.
    """
    retrieved_knowledge = search_knowledge_base(user_query)
    retrieved_db = search_erp_database(user_query, db=db) if db else {}
    
    # Synthesize Context Summary
    context_lines = []
    
    if retrieved_knowledge:
        context_lines.append("--- RETRIEVED REGULATORY KNOWLEDGE ---")
        for k in retrieved_knowledge:
            context_lines.append(f"• [{k['category']}] {k['title']}: {k['content']}")

    db_found = False
    if retrieved_db.get("customers"):
        db_found = True
        context_lines.append("\n--- MATCHED CLIENTS IN DATABASE ---")
        for c in retrieved_db["customers"]:
            context_lines.append(f"• Client: {c['name']} | VAT: {c['vat_number']} | CR: {c['cr_number']}")

    if retrieved_db.get("invoices"):
        db_found = True
        context_lines.append("\n--- MATCHED INVOICES IN DATABASE ---")
        for i in retrieved_db["invoices"]:
            context_lines.append(f"• Invoice {i['invoice_number']} | Client: {i['client']} | Total: SAR {i['total_amount']:,.2f} | Status: {i['status']}")

    if retrieved_db.get("employees"):
        db_found = True
        context_lines.append("\n--- MATCHED EMPLOYEES IN DATABASE ---")
        for e in retrieved_db["employees"]:
            context_lines.append(f"• Employee {e['emp_id']} ({e['name']}) - {e['nationality']} | Dept: {e['department']}")

    synthesized_answer = "\n".join(context_lines) if context_lines else "No specific matching records or rules found for your query. Please try searching with a client name, invoice number, or labor law term."

    return {
        "query": user_query,
        "retrieved_knowledge_count": len(retrieved_knowledge),
        "matched_db_records": db_found,
        "synthesized_response": synthesized_answer,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
