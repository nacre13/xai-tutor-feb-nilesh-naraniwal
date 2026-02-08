"""
Read-only Client API for seed data.
List and get clients by ID (e.g. for dropdowns when creating invoices).
"""

from fastapi import APIRouter, HTTPException, Query

from app.database import get_db

router = APIRouter(prefix="/clients", tags=["clients"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get("")
def list_clients(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
):
    """List clients with pagination (seed data)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients")
            total = cursor.fetchone()[0]
            offset = (page - 1) * page_size
            cursor.execute(
                """
                SELECT id, name, address, company_registration_no
                FROM clients
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            )
            rows = cursor.fetchall()
            total_pages = (total + page_size - 1) // page_size if page_size else 0
            return {
                "clients": [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "address": r["address"],
                        "company_registration_no": r["company_registration_no"],
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


@router.get("/{client_id}")
def get_client(client_id: int):
    """Get a single client by ID (seed data)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, address, company_registration_no FROM clients WHERE id = ?",
                (client_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Client not found")
            return {
                "id": row["id"],
                "name": row["name"],
                "address": row["address"],
                "company_registration_no": row["company_registration_no"],
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
