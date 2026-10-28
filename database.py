import sqlite3
import os

DB_PATH = 'accounts.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")   # multi-reader safe
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS accounts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT    NOT NULL,
            aging   TEXT    NOT NULL,
            file_path TEXT  NOT NULL,
            status  TEXT    DEFAULT 'available'
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            amount_ton REAL    NOT NULL,
            comment    TEXT    NOT NULL UNIQUE,
            status     TEXT    DEFAULT 'pending',
            method     TEXT    DEFAULT 'ton'
        );
    ''')
    # Safe migration: add columns if they don't exist yet
    for col, definition in [
        ("method", "TEXT DEFAULT 'ton'"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

def add_account(country, aging, file_path):
    conn = get_conn()
    conn.execute(
        'INSERT INTO accounts (country, aging, file_path) VALUES (?, ?, ?)',
        (country, aging, file_path)
    )
    conn.commit()
    conn.close()

def get_available_accounts():
    conn = get_conn()
    rows = conn.execute(
        'SELECT id, country, aging FROM accounts WHERE status="available"'
    ).fetchall()
    conn.close()
    return rows

def get_account(account_id):
    conn = get_conn()
    row = conn.execute(
        'SELECT * FROM accounts WHERE id=? AND status="available"',
        (account_id,)
    ).fetchone()
    conn.close()
    return row

def reserve_account(account_id) -> bool:
    """
    Atomically marks account as 'reserved'.
    Returns True if reservation succeeded, False if already taken.
    This prevents two buyers getting the same account (race condition fix).
    """
    conn = get_conn()
    try:
        cursor = conn.execute(
            'UPDATE accounts SET status="reserved" WHERE id=? AND status="available"',
            (account_id,)
        )
        conn.commit()
        return cursor.rowcount == 1   # 0 means someone else grabbed it first
    finally:
        conn.close()

def mark_account_sold(account_id):
    conn = get_conn()
    conn.execute('UPDATE accounts SET status="sold" WHERE id=?', (account_id,))
    conn.commit()
    conn.close()

def release_account(account_id):
    """Release a reserved account back to 'available' (e.g. payment timeout)."""
    conn = get_conn()
    conn.execute(
        'UPDATE accounts SET status="available" WHERE id=? AND status="reserved"',
        (account_id,)
    )
    conn.commit()
    conn.close()

def delete_account(account_id):
    conn = get_conn()
    conn.execute('UPDATE accounts SET status="deleted" WHERE id=?', (account_id,))
    conn.commit()
    conn.close()

def create_invoice(user_id, account_id, amount_ton, comment, method='ton'):
    conn = get_conn()
    conn.execute(
        '''INSERT OR IGNORE INTO invoices
           (user_id, account_id, amount_ton, comment, method)
           VALUES (?, ?, ?, ?, ?)''',
        (user_id, account_id, amount_ton, comment, method)
    )
    conn.commit()
    conn.close()

def get_invoice(comment):
    conn = get_conn()
    row = conn.execute(
        'SELECT * FROM invoices WHERE comment=?', (comment,)
    ).fetchone()
    conn.close()
    return row

def mark_invoice_paid(comment):
    conn = get_conn()
    conn.execute(
        'UPDATE invoices SET status="paid" WHERE comment=?', (comment,)
    )
    conn.commit()
    conn.close()
