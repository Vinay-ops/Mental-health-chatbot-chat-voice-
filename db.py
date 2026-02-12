import os
import mysql.connector
from mysql.connector import Error

def get_conn():
    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "vinay"),
            database=os.getenv("MYSQL_DB", "rm"),
        )
    except Error:
        return None

def ensure_schema():
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS chat_logs ("
            "id INT AUTO_INCREMENT PRIMARY KEY, "
            "ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "role VARCHAR(16) NOT NULL, "
            "content TEXT NOT NULL)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INT AUTO_INCREMENT PRIMARY KEY, "
            "email VARCHAR(255) UNIQUE NOT NULL, "
            "password_hash VARCHAR(255) NOT NULL, "
            "name VARCHAR(255) NOT NULL, "
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def save_log(role: str, content: str):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_logs (role, content) VALUES (%s, %s)",
            (role, content),
        )
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def get_user_by_email(email: str):
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, email, password_hash, name FROM users WHERE email=%s", (email,))
        row = cur.fetchone()
        return row
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def create_user(email: str, password_hash: str, name: str):
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)",
            (email, password_hash, name),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
