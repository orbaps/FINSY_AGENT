# app/utils.py
import sqlite3
import os
import json
import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

# Simple connection pool using context manager
_db_path: Optional[str] = None


def init_db(db_path: str) -> None:
    """Initialize database with tables and indexes"""
    global _db_path
    _db_path = db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
          invoice_id TEXT PRIMARY KEY,
          vendor TEXT,
          date TEXT,
          total REAL,
          currency TEXT,
          po_number TEXT,
          confidence REAL,
          raw_file TEXT,
          created_at TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
          approval_id TEXT PRIMARY KEY,
          invoice_id TEXT,
          requester TEXT,
          approver TEXT,
          reason TEXT,
          status TEXT,
          comment TEXT,
          created_at TEXT,
          updated_at TEXT
        )""")
        # Create indexes for better performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_approvals_invoice_id ON approvals(invoice_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_invoices_vendor ON invoices(vendor)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date)")
        conn.commit()


@contextmanager
def _get_connection(db_path: Optional[str] = None):
    """Context manager for database connections"""
    target_path = db_path or _db_path
    if target_path is None:
        raise ValueError("Database path not specified and not initialized.")
    
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def save_invoice_record(db_path: str, invoice: Dict[str, Any], raw_file_name: Optional[str] = None) -> None:
    """Save invoice record to database"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        c.execute("""
            INSERT OR REPLACE INTO invoices(
                invoice_id, vendor, date, total, currency, po_number, 
                confidence, raw_file, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            invoice['invoice_id'], 
            invoice.get('vendor'), 
            invoice.get('date'), 
            invoice.get('total'), 
            invoice.get('currency', 'USD'), 
            invoice.get('po_number'), 
            invoice.get('confidence'), 
            raw_file_name, 
            now
        ))


def get_invoice(db_path: str, invoice_id: str) -> Optional[Dict[str, Any]]:
    """Get invoice by ID"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT invoice_id, vendor, date, total, currency, po_number, 
                   confidence, raw_file, created_at 
            FROM invoices WHERE invoice_id = ?
        """, (invoice_id,))
        row = c.fetchone()
        if not row:
            return None
        return dict(row)


def list_invoices(db_path: str, limit: int = 100, offset: int = 0, 
                  vendor: Optional[str] = None) -> List[Dict[str, Any]]:
    """List invoices with pagination and optional filtering"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        query = "SELECT invoice_id, vendor, date, total, currency, po_number, confidence, created_at FROM invoices"
        params = []
        
        if vendor:
            query += " WHERE vendor LIKE ?"
            params.append(f"%{vendor}%")
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        c.execute(query, params)
        rows = c.fetchall()
        return [dict(row) for row in rows]

def save_approval(db_path: str, approval_record: Dict[str, Any]) -> None:
    """Save approval record to database"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        c.execute("""
            INSERT INTO approvals(
                approval_id, invoice_id, requester, approver, reason, status, created_at
            ) VALUES (?,?,?,?,?,?,?)
        """, (
            approval_record['approval_id'], 
            approval_record['invoice_id'], 
            approval_record.get('requester'), 
            approval_record.get('approver'), 
            approval_record['reason'], 
            approval_record['status'], 
            now
        ))


def update_approval(db_path: str, approval_id: str, action: str, 
                   comment: Optional[str] = None, approver: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update approval status"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        status = "approved" if action == "approve" else "rejected"
        now = datetime.datetime.utcnow().isoformat()
        c.execute("""
            UPDATE approvals 
            SET status=?, comment=?, updated_at=?, approver=COALESCE(?, approver)
            WHERE approval_id=?
        """, (status, comment, now, approver, approval_id))
        
        c.execute("""
            SELECT a.approval_id, a.invoice_id, a.requester, a.approver, a.reason, a.status, 
                   a.comment, a.created_at, a.updated_at, i.total as amount, i.vendor
            FROM approvals a
            LEFT JOIN invoices i ON a.invoice_id = i.invoice_id
            WHERE a.approval_id=?
        """, (approval_id,))
        row = c.fetchone()
        if not row:
            return None
        return dict(row)


def get_approval(db_path: str, approval_id: str) -> Optional[Dict[str, Any]]:
    """Get approval by ID"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT a.approval_id, a.invoice_id, a.requester, a.approver, a.reason, a.status, 
                   a.comment, a.created_at, a.updated_at, i.total as amount, i.vendor
            FROM approvals a
            LEFT JOIN invoices i ON a.invoice_id = i.invoice_id
            WHERE a.approval_id=?
        """, (approval_id,))
        row = c.fetchone()
        if not row:
            return None
        return dict(row)


def list_approvals(db_path: str, status: Optional[str] = None, 
                   limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List approvals with optional status filter"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        query = """
            SELECT a.approval_id, a.invoice_id, a.requester, a.approver, a.reason, a.status, 
                   a.comment, a.created_at, a.updated_at, i.total as amount, i.vendor
            FROM approvals a
            LEFT JOIN invoices i ON a.invoice_id = i.invoice_id
        """
        params = []
        
        if status:
            query += " WHERE a.status = ?"
            params.append(status)
        
        query += " ORDER BY a.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        c.execute(query, params)
        rows = c.fetchall()
        return [dict(row) for row in rows]


def get_pending_approvals(db_path: str) -> List[Dict[str, Any]]:
    """Get all pending approvals"""
    return list_approvals(db_path, status='pending')

def summary_report(db_path: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None) -> Dict[str, Any]:
    """Generate summary report"""
    with _get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT count(*) FROM invoices")
        total_invoices = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM approvals WHERE status='approved'")
        approved = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM approvals WHERE status='pending'")
        pending = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM approvals WHERE status='rejected'")
        rejected = c.fetchone()[0]
        
        return {
            "total_invoices": total_invoices,
            "approved_approvals": approved,
            "pending_approvals": pending,
            "rejected_approvals": rejected,
            "period": {"start": start_date, "end": end_date}
        }
