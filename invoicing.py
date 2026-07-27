"""
ZATCA (FATOORA) Saudi Arabia Invoicing & Billing Logic Engine
Fully compliant with ZATCA Tax Invoices (B2B) and Simplified Tax Invoices (B2C).
Includes TLV Base64 QR Code Generator, 15% VAT calculation, and Payment Lifecycle Management.
"""

import base64
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from database import SessionLocal, Customer, Invoice, InvoiceItem, CatalogItem, CompanySettings


def encode_tlv(tag: int, value: str) -> bytes:
    """Encode Tag-Length-Value (TLV) byte structure according to ZATCA standards."""
    val_bytes = str(value).encode('utf-8')
    return bytes([tag, len(val_bytes)]) + val_bytes


def generate_zatca_qr_base64(seller_name: str, vat_number: str, timestamp_str: str,
                           total_amount: float, vat_amount: float) -> str:
    """
    Generate ZATCA TLV Base64 QR Code string for Saudi E-Invoicing (FATOORA).
    Tags required by ZATCA:
      Tag 1: Seller Name
      Tag 2: Seller VAT Registration Number (15 digits)
      Tag 3: Timestamp (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)
      Tag 4: Invoice Total (with VAT)
      Tag 5: VAT Total
    """
    try:
        seller_clean = seller_name.strip() if seller_name else "Saudi Enterprise Corp"
        vat_clean = vat_number.strip() if vat_number else "310000000000003"
        ts_clean = timestamp_str.strip() if timestamp_str else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        tlv_data = (
            encode_tlv(1, seller_clean) +
            encode_tlv(2, vat_clean) +
            encode_tlv(3, ts_clean) +
            encode_tlv(4, f"{max(0.0, total_amount):.2f}") +
            encode_tlv(5, f"{max(0.0, vat_amount):.2f}")
        )
        return base64.b64encode(tlv_data).decode('utf-8')
    except Exception as e:
        print(f"Error generating ZATCA QR Code: {e}")
        return ""


def calculate_invoice_totals(line_items: List[Dict[str, any]]) -> Dict[str, float]:
    """
    Calculate itemized line item subtotals (Govt Fee + Service Charges), 15% VAT on Service Charges, and Net Invoice Total.
    Each item dict contains: 'description', 'beneficiary_name', 'quantity', 'govt_fee', 'service_charge', 'unit_price', 'vat_rate' (0.15).
    """
    subtotal = 0.0
    vat_total = 0.0
    total_govt_fees = 0.0
    total_service_charges = 0.0
    processed_items = []

    for item in line_items:
        qty = max(1.0, float(item.get('quantity', 1.0)))
        g_fee = round(max(0.0, float(item.get('govt_fee', 0.0))) * qty, 2)
        
        # If service_charge not explicitly passed, fallback to unit_price
        s_charge_raw = item.get('service_charge', item.get('unit_price', 0.0))
        s_charge = round(max(0.0, float(s_charge_raw)) * qty, 2)
        
        vat_rate = float(item.get('vat_rate', 0.15))
        
        # VAT applies to Service Charges
        item_vat = round(s_charge * vat_rate, 2)
        item_subtotal = round(g_fee + s_charge, 2)
        item_total = round(item_subtotal + item_vat, 2)

        subtotal += item_subtotal
        vat_total += item_vat
        total_govt_fees += g_fee
        total_service_charges += s_charge

        processed_items.append({
            "description": item.get('description', 'Service Item'),
            "beneficiary_name": item.get('beneficiary_name', ''),
            "quantity": qty,
            "unit_price": s_charge / qty if qty > 0 else 0.0,
            "govt_fee": g_fee,
            "service_charge": s_charge,
            "vat_rate": vat_rate,
            "vat_amount": item_vat,
            "subtotal": item_subtotal,
            "total_amount": item_total
        })

    total_amount = round(subtotal + vat_total, 2)

    return {
        "subtotal": round(subtotal, 2),
        "total_govt_fees": round(total_govt_fees, 2),
        "total_service_charges": round(total_service_charges, 2),
        "vat_total": round(vat_total, 2),
        "total_amount": total_amount,
        "items": processed_items
    }


def generate_next_invoice_number(db: Session) -> str:
    """Generate sequential invoice number e.g. INV-2026-0001"""
    year = datetime.now().year
    count = db.query(Invoice).count() + 1
    return f"INV-{year}-{count:04d}"


def create_invoice(invoice_data: Dict[str, any], line_items: List[Dict[str, any]], db: Optional[Session] = None) -> Dict[str, any]:
    """
    Create a new Tax Invoice with itemized line items, beneficiary details, government fees, service charges, and QR Code.
    """
    session = SessionLocal() if db is None else db
    try:
        customer_id = int(invoice_data.get("customer_id"))
        customer = session.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": f"Customer ID {customer_id} not found", "success": False}

        company = session.query(CompanySettings).first()
        if not company:
            company = CompanySettings()

        # Calculate Totals
        calc = calculate_invoice_totals(line_items)
        
        inv_num = invoice_data.get("invoice_number") or generate_next_invoice_number(session)
        issue_date_str = invoice_data.get("issue_date")
        try:
            issue_dt = datetime.fromisoformat(issue_date_str) if issue_date_str else datetime.utcnow()
        except:
            issue_dt = datetime.utcnow()

        due_date_str = invoice_data.get("due_date")
        try:
            due_dt = datetime.fromisoformat(due_date_str) if due_date_str else (issue_dt + timedelta(days=30))
        except:
            due_dt = issue_dt + timedelta(days=30)

        # Generate Base64 TLV QR Code
        qr_code = generate_zatca_qr_base64(
            seller_name=company.establishment_name,
            vat_number=company.vat_number,
            timestamp_str=issue_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            total_amount=calc["total_amount"],
            vat_amount=calc["vat_total"]
        )

        new_invoice = Invoice(
            invoice_number=inv_num,
            invoice_type=invoice_data.get("invoice_type", "Tax Invoice"),
            issue_date=issue_dt,
            due_date=due_dt,
            customer_id=customer_id,
            subtotal=calc["subtotal"],
            vat_total=calc["vat_total"],
            total_amount=calc["total_amount"],
            paid_amount=float(invoice_data.get("paid_amount", 0.0)),
            status=invoice_data.get("status", "Issued"),
            notes=invoice_data.get("notes"),
            zatca_qr_code=qr_code
        )

        session.add(new_invoice)
        session.commit()
        session.refresh(new_invoice)

        # Add Line Items
        for item in calc["items"]:
            inv_item = InvoiceItem(
                invoice_id=new_invoice.id,
                description=item["description"],
                beneficiary_name=item["beneficiary_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                govt_fee=item["govt_fee"],
                service_charge=item["service_charge"],
                vat_rate=item["vat_rate"],
                vat_amount=item["vat_amount"],
                subtotal=item["subtotal"],
                total_amount=item["total_amount"]
            )
            session.add(inv_item)

        session.commit()

        return {
            "success": True,
            "invoice_id": new_invoice.id,
            "invoice_number": new_invoice.invoice_number,
            "customer_name": customer.customer_name,
            "subtotal": new_invoice.subtotal,
            "vat_total": new_invoice.vat_total,
            "total_amount": new_invoice.total_amount,
            "status": new_invoice.status,
            "zatca_qr_code": new_invoice.zatca_qr_code
        }

    except Exception as e:
        session.rollback()
        return {"error": str(e), "success": False}
    finally:
        if db is None:
            session.close()


def record_invoice_payment(invoice_id: int, payment_amount: float, db: Optional[Session] = None) -> Dict[str, any]:
    """Record a payment against an invoice and update its lifecycle status."""
    session = SessionLocal() if db is None else db
    try:
        invoice = session.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": "Invoice not found", "success": False}

        invoice.paid_amount = round((invoice.paid_amount or 0.0) + max(0.0, payment_amount), 2)
        
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = "Paid"
        elif invoice.paid_amount > 0:
            invoice.status = "Partially Paid"

        session.commit()
        session.refresh(invoice)

        return {
            "success": True,
            "invoice_number": invoice.invoice_number,
            "paid_amount": invoice.paid_amount,
            "total_amount": invoice.total_amount,
            "status": invoice.status
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e), "success": False}
    finally:
        if db is None:
            session.close()


def get_invoicing_kpis(db: Optional[Session] = None) -> Dict[str, any]:
    """Calculate executive billing KPIs (Total Invoiced, Paid, Outstanding, Overdue Count)."""
    session = SessionLocal() if db is None else db
    try:
        invoices = session.query(Invoice).filter(Invoice.status != "Cancelled").all()
        now = datetime.utcnow()

        total_invoiced = sum(i.total_amount for i in invoices)
        total_paid = sum(i.paid_amount or 0.0 for i in invoices)
        outstanding = max(0.0, total_invoiced - total_paid)
        
        overdue_count = 0
        for i in invoices:
            if i.status not in ["Paid", "Cancelled"] and i.due_date and i.due_date < now:
                overdue_count += 1

        return {
            "total_invoices_count": len(invoices),
            "total_invoiced_sar": round(total_invoiced, 2),
            "total_paid_sar": round(total_paid, 2),
            "outstanding_receivables_sar": round(outstanding, 2),
            "overdue_invoices_count": overdue_count
        }
    finally:
        if db is None:
            session.close()


def generate_customer_statement(customer_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, any]:
    """
    Generate Statement of Account (SOA) for a given B2B Client with running ledger balance.
    """
    session = SessionLocal() if db is None else db
    try:
        customer = session.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"error": f"Customer ID {customer_id} not found", "success": False}

        company = session.query(CompanySettings).first() or CompanySettings()

        query = session.query(Invoice).filter(Invoice.customer_id == customer_id, Invoice.status != "Cancelled")
        
        if start_date:
            try:
                s_dt = datetime.fromisoformat(start_date)
                query = query.filter(Invoice.issue_date >= s_dt)
            except:
                pass

        if end_date:
            try:
                e_dt = datetime.fromisoformat(end_date)
                query = query.filter(Invoice.issue_date <= e_dt)
            except:
                pass

        invoices = query.order_by(Invoice.issue_date.asc()).all()

        ledger_entries = []
        running_balance = 0.0
        total_billed = 0.0
        total_paid = 0.0

        for inv in invoices:
            billed_amt = inv.total_amount
            paid_amt = inv.paid_amount or 0.0
            total_billed += billed_amt
            total_paid += paid_amt
            
            # Entry 1: Invoice Billed
            running_balance += billed_amt
            ledger_entries.append({
                "date": inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else "N/A",
                "reference": inv.invoice_number,
                "type": "Tax Invoice",
                "billed_sar": billed_amt,
                "paid_sar": 0.0,
                "running_balance_sar": round(running_balance, 2),
                "status": inv.status
            })

            # Entry 2: Payment Received (if any)
            if paid_amt > 0:
                running_balance -= paid_amt
                ledger_entries.append({
                    "date": inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else "N/A",
                    "reference": f"PAY-{inv.invoice_number}",
                    "type": "Payment Received",
                    "billed_sar": 0.0,
                    "paid_sar": paid_amt,
                    "running_balance_sar": round(running_balance, 2),
                    "status": "Cleared"
                })

        outstanding = max(0.0, total_billed - total_paid)

        return {
            "success": True,
            "seller": {
                "name": company.establishment_name,
                "cr_number": company.cr_number,
                "vat_number": company.vat_number,
                "iban": company.company_iban
            },
            "customer": {
                "id": customer.id,
                "name": customer.customer_name,
                "vat_number": customer.vat_number,
                "cr_number": customer.cr_number,
                "email": customer.email,
                "phone": customer.phone,
                "address": customer.address,
                "city": customer.city
            },
            "statement_summary": {
                "total_billed_sar": round(total_billed, 2),
                "total_paid_sar": round(total_paid, 2),
                "outstanding_balance_sar": round(outstanding, 2),
                "statement_date": datetime.now().strftime("%Y-%m-%d")
            },
            "ledger_entries": ledger_entries
        }
    except Exception as e:
        return {"error": str(e), "success": False}
    finally:
        if db is None:
            session.close()

