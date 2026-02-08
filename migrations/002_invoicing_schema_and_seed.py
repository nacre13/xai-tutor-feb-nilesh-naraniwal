"""
Migration: Invoicing schema and seed data
Version: 002
Description: Creates products, clients, invoices, invoice_items tables and seeds products/clients
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import DATABASE_PATH


def _ensure_migrations_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def upgrade():
    """Apply the migration."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    _ensure_migrations_table(cursor)
    cursor.execute("SELECT 1 FROM _migrations WHERE name = ?", ("002_invoicing_schema_and_seed",))
    if cursor.fetchone():
        print("Migration 002_invoicing_schema_and_seed already applied. Skipping.")
        conn.close()
        return

    # Products (seed only): name, price
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    # Clients (seed only): name, address, company registration no.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            company_registration_no TEXT NOT NULL
        )
    """)

    # Invoices: invoice_no, issue_date, due_date, client_id, address, tax, total
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL UNIQUE,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            address TEXT NOT NULL,
            tax REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Invoice line items: invoice_id, product_id, quantity, unit_price, line_total
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL
        )
    """)

    # Seed products
    products = [
        ("Widget A", 10.00),
        ("Widget B", 25.50),
        ("Service Hour", 75.00),
        ("License Fee", 199.00),
    ]
    cursor.executemany("INSERT INTO products (name, price) VALUES (?, ?)", products)

    # Seed clients
    clients = [
        ("Acme Corp", "123 Main St, City A", "REG-001"),
        ("Beta Ltd", "456 Oak Ave, City B", "REG-002"),
        ("Gamma Inc", "789 Pine Rd, City C", "REG-003"),
    ]
    cursor.executemany(
        "INSERT INTO clients (name, address, company_registration_no) VALUES (?, ?, ?)",
        clients,
    )

    cursor.execute("INSERT INTO _migrations (name) VALUES (?)", ("002_invoicing_schema_and_seed",))
    conn.commit()
    conn.close()
    print("Migration 002_invoicing_schema_and_seed applied successfully.")


def downgrade():
    """Revert the migration."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS invoice_items")
    cursor.execute("DROP TABLE IF EXISTS invoices")
    cursor.execute("DROP TABLE IF EXISTS clients")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DELETE FROM _migrations WHERE name = ?", ("002_invoicing_schema_and_seed",))

    conn.commit()
    conn.close()
    print("Migration 002_invoicing_schema_and_seed reverted successfully.")
