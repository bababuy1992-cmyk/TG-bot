import sqlite3
import os

DB_PATH = 'accounts.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            aging TEXT NOT NULL,
            file_path TEXT NOT NULL,
            status TEXT DEFAULT 'available'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            amount_ton REAL NOT NULL,
            comment TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    # Migrate DB if needed
    try:
        cursor.execute("ALTER TABLE invoices ADD COLUMN method TEXT DEFAULT 'ton'")
    except sqlite3.OperationalError:
        pass # column already exists
        
    conn.commit()
    conn.close()

def add_account(country, aging, file_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO accounts (country, aging, file_path)
        VALUES (?, ?, ?)
    ''', (country, aging, file_path))
    conn.commit()
    conn.close()

def get_available_accounts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, country, aging FROM accounts WHERE status="available"')
    res = cursor.fetchall()
    conn.close()
    return res

def get_account(account_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM accounts WHERE id=? AND status="available"', (account_id,))
    res = cursor.fetchone()
    conn.close()
    return res

def mark_account_sold(account_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE accounts SET status="sold" WHERE id=?', (account_id,))
    conn.commit()
    conn.close()

def delete_account(account_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE accounts SET status="deleted" WHERE id=?', (account_id,))
    conn.commit()
    conn.close()

def create_invoice(user_id, account_id, amount_ton, comment, method='ton'):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO invoices (user_id, account_id, amount_ton, comment, method)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, account_id, amount_ton, comment, method))
    conn.commit()
    conn.close()

def get_invoice(comment):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM invoices WHERE comment=?', (comment,))
    res = cursor.fetchone()
    conn.close()
    return res

def mark_invoice_paid(comment):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE invoices SET status="paid" WHERE comment=?', (comment,))
    conn.commit()
    conn.close()
