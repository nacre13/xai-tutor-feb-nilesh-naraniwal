"""
Read-only Product API for seed data.
List and get products by ID (e.g. for line items when creating invoices).
"""

from fastapi import APIRouter, HTTPException, Query

from app.database import get_db

router = APIRouter(prefix="/products", tags=["products"])

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.get("")
def list_products(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
):
    """List products with pagination (seed data)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            total = cursor.fetchone()[0]
            offset = (page - 1) * page_size
            cursor.execute(
                """
                SELECT id, name, price
                FROM products
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            )
            rows = cursor.fetchall()
            total_pages = (total + page_size - 1) // page_size if page_size else 0
            return {
                "products": [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "price": r["price"],
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


@router.get("/{product_id}")
def get_product(product_id: int):
    """Get a single product by ID (seed data)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, price FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Product not found")
            return {
                "id": row["id"],
                "name": row["name"],
                "price": row["price"],
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
