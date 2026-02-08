"""
Debug and Support APIs for development and troubleshooting.
Provides database stats, migration status, and system information.
"""

import os
import glob
import sqlite3
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from app.database import DATABASE_PATH, get_db

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/info")
def get_system_info():
    """Get system information: version, database path, etc."""
    return {
        "api_version": "1.0.0",
        "database_path": DATABASE_PATH,
        "database_exists": os.path.exists(DATABASE_PATH),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/db/health")
def check_database_health():
    """Check database connection and basic health."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return {
                "status": "healthy",
                "connected": True,
                "database_path": DATABASE_PATH,
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
            "database_path": DATABASE_PATH,
        }


@router.get("/db/stats")
def get_database_stats():
    """Get database statistics: table counts, etc."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            stats = {}
            tables = ["clients", "products", "invoices", "invoice_items"]
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    stats[table] = None  # Table doesn't exist
            
            # Get database file size if exists
            db_size = None
            if os.path.exists(DATABASE_PATH):
                db_size = os.path.getsize(DATABASE_PATH)
            
            return {
                "table_counts": stats,
                "database_size_bytes": db_size,
                "database_path": DATABASE_PATH,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/migrations")
def get_migration_status():
    """Get migration status: which migrations are applied."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("SELECT name, applied_at FROM _migrations ORDER BY id")
            applied = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get all migration files
        migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "migrations")
        pattern = os.path.join(migrations_dir, "[0-9][0-9][0-9]_*.py")
        files = sorted(glob.glob(pattern))
        migration_files = [os.path.basename(f).replace(".py", "") for f in files]
        
        migrations_status = []
        for mig_name in migration_files:
            migrations_status.append({
                "name": mig_name,
                "status": "applied" if mig_name in applied else "pending",
                "applied_at": applied.get(mig_name),
            })
        
        return {
            "migrations": migrations_status,
            "total": len(migration_files),
            "applied": len(applied),
            "pending": len(migration_files) - len(applied),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/schema")
def get_database_schema():
    """Get database schema: table names and their column info."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = []
                for col in cursor.fetchall():
                    columns.append({
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "default": col[4],
                        "primary_key": bool(col[5]),
                    })
                schema[table] = columns
            
            return {
                "tables": list(schema.keys()),
                "schema": schema,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/endpoints")
def list_endpoints():
    """List all available API endpoints (useful for discovery)."""
    # FastAPI provides this via /openapi.json, but this is a simpler summary
    return {
        "endpoints": {
            "health": ["GET /health"],
            "clients": [
                "GET /clients",
                "GET /clients/{client_id}",
            ],
            "products": [
                "GET /products",
                "GET /products/{product_id}",
            ],
            "invoices": [
                "GET /invoices",
                "POST /invoices",
                "GET /invoices/{invoice_id}",
                "DELETE /invoices/{invoice_id}",
            ],
            "debug": [
                "GET /debug/info",
                "GET /debug/db/health",
                "GET /debug/db/stats",
                "GET /debug/db/migrations",
                "GET /debug/db/schema",
                "GET /debug/endpoints",
            ],
            "docs": [
                "GET /docs (Swagger UI)",
                "GET /openapi.json (OpenAPI schema)",
                "GET /redoc (ReDoc)",
            ],
        },
        "note": "Use /docs for interactive API documentation",
    }
