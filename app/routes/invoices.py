"""
Invoice API: create, list, get by ID, delete.
Products and clients are seed data only (no APIs); referenced by id when creating invoices.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_db

# Pagination defaults and limits
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

router = APIRouter(prefix="/invoices", tags=["invoices"])


# --- Pydantic models ---

class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: float = Field(gt=0, description="Quantity must be positive")


class InvoiceCreate(BaseModel):
    invoice_no: str
    issue_date: date
    due_date: date
    client_id: int
    address: str
    items: list[InvoiceItemCreate] = Field(min_length=1, description="At least one line item")
    tax: float = Field(ge=0, default=0.0)


class InvoiceItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: float
    unit_price: float
    line_total: float


class ClientRef(BaseModel):
    id: int
    name: str
    address: str
    company_registration_no: str


class InvoiceResponse(BaseModel):
    id: int
    invoice_no: str
    issue_date: str
    due_date: str
    client: ClientRef
    address: str
    items: list[InvoiceItemResponse]
    tax: float
    total: float


def _row_to_client_ref(row: Any) -> ClientRef:
    return ClientRef(
        id=row["id"],
        name=row["name"],
        address=row["address"],
        company_registration_no=row["company_registration_no"],
    )


def _row_to_invoice_item_response(row: Any) -> InvoiceItemResponse:
    return InvoiceItemResponse(
        product_id=row["product_id"],
        product_name=row["product_name"],
        quantity=row["quantity"],
        unit_price=row["unit_price"],
        line_total=row["line_total"],
    )


@router.post("", status_code=201)
def create_invoice(body: InvoiceCreate):
    """Create a new invoice. Client and products are referenced by id (seed data)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, name, address, company_registration_no FROM clients WHERE id = ?", (body.client_id,))
            client_row = cursor.fetchone()
            if client_row is None:
                raise HTTPException(status_code=400, detail="Invalid client_id")

            subtotal = Decimal("0")
            line_rows = []
            for line in body.items:
                cursor.execute("SELECT id, name, price FROM products WHERE id = ?", (line.product_id,))
                prod = cursor.fetchone()
                if prod is None:
                    raise HTTPException(status_code=400, detail=f"Invalid product_id: {line.product_id}")
                unit_price = float(prod["price"])
                qty = line.quantity
                line_total = round(unit_price * qty, 2)
                subtotal += Decimal(str(line_total))
                line_rows.append((line.product_id, prod["name"], qty, unit_price, line_total))

            total = float(subtotal) + body.tax
            total = round(total, 2)

            cursor.execute(
                """INSERT INTO invoices (invoice_no, issue_date, due_date, client_id, address, tax, total)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    body.invoice_no,
                    body.issue_date.isoformat(),
                    body.due_date.isoformat(),
                    body.client_id,
                    body.address,
                    body.tax,
                    total,
                ),
            )
            invoice_id = cursor.lastrowid

            for product_id, _pn, qty, unit_price, line_total in line_rows:
                cursor.execute(
                    """INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price, line_total)
                       VALUES (?, ?, ?, ?, ?)""",
                    (invoice_id, product_id, qty, unit_price, line_total),
                )

            # Build response
            client = _row_to_client_ref(client_row)
            items_resp = [
                InvoiceItemResponse(
                    product_id=pid,
                    product_name=pn,
                    quantity=q,
                    unit_price=up,
                    line_total=lt,
                )
                for pid, pn, q, up, lt in line_rows
            ]
            return InvoiceResponse(
                id=invoice_id,
                invoice_no=body.invoice_no,
                issue_date=body.issue_date.isoformat(),
                due_date=body.due_date.isoformat(),
                client=client,
                address=body.address,
                items=items_resp,
                tax=body.tax,
                total=total,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def list_invoices(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
):
    """List invoices with pagination (id, invoice_no, issue_date, due_date, total)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Total count (single scalar query)
            cursor.execute("SELECT COUNT(*) FROM invoices")
            total = cursor.fetchone()[0]
            # Page of rows using LIMIT/OFFSET
            offset = (page - 1) * page_size
            cursor.execute(
                """
                SELECT i.id, i.invoice_no, i.issue_date, i.due_date, i.total
                FROM invoices i
                ORDER BY i.id
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            )
            rows = cursor.fetchall()
            total_pages = (total + page_size - 1) // page_size if page_size else 0
            return {
                "invoices": [
                    {
                        "id": r["id"],
                        "invoice_no": r["invoice_no"],
                        "issue_date": r["issue_date"],
                        "due_date": r["due_date"],
                        "total": r["total"],
                    }
                    for r in rows
                ],
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                },
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int):
    """Get a single invoice by ID with full client and line items."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.id, i.invoice_no, i.issue_date, i.due_date, i.client_id, i.address, i.tax, i.total,
                       c.id AS c_id, c.name AS c_name, c.address AS c_address, c.company_registration_no
                FROM invoices i
                JOIN clients c ON c.id = i.client_id
                WHERE i.id = ?
            """, (invoice_id,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Invoice not found")

            client = ClientRef(
                id=row["c_id"],
                name=row["c_name"],
                address=row["c_address"],
                company_registration_no=row["company_registration_no"],
            )

            cursor.execute("""
                SELECT ii.product_id, p.name AS product_name, ii.quantity, ii.unit_price, ii.line_total
                FROM invoice_items ii
                JOIN products p ON p.id = ii.product_id
                WHERE ii.invoice_id = ?
            """, (invoice_id,))
            item_rows = cursor.fetchall()
            items = [_row_to_invoice_item_response(r) for r in item_rows]

            return InvoiceResponse(
                id=row["id"],
                invoice_no=row["invoice_no"],
                issue_date=row["issue_date"],
                due_date=row["due_date"],
                client=client,
                address=row["address"],
                items=items,
                tax=row["tax"],
                total=row["total"],
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int):
    """Delete an invoice by ID. Line items are removed by CASCADE."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Invoice not found")
            cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
            cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
            return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
