import sqlite3
from .settings import settings
from typing import Optional
from rich import print_json


"""
CREATE TABLE company (
    oid TEXT PRIMARY KEY,
    title TEXT,
    address TEXT,
    town TEXT,
    searchstr TEXT,
    rating_2gis REAL,
    trusted BOOLEAN,
    nreviews INTEGER,
    detections TEXT
);
"""

def make_connection():
    return sqlite3.connect(settings.companydb)

# Function to check if oid exists in the "company" table
def check_by_oid(oid: str, conn = None):
    conn = conn or make_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM company WHERE oid = ?", (oid,))
    result = cursor.fetchone()
    return result is not None  # If result is None, the oid doesn't exist

def get_by_oid(oid: str, conn = None) -> Optional[dict]:
    conn = conn or make_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM company WHERE oid = ?", (oid,))
    row = cursor.fetchone()
    if row is None:
        return None

    # Map column names to values
    col_names = [desc[0] for desc in cursor.description]
    return dict(zip(col_names, row))

def dbsearch(query: str, limit=20, conn = None) -> list[dict]:
    conn = conn or make_connection()
    words = query.strip().lower().split()
    if not words:
        return []

    clauses = " AND ".join(["searchstr LIKE ? "] * len(words))
    params = [f"%{w}%" for w in words]

    sql = f"SELECT * FROM company WHERE {clauses} LIMIT {limit}"
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    col_names = [desc[0] for desc in cursor.description]
    return [dict(zip(col_names, row)) for row in rows]

def dbtruncate(conn = None):
    conn = conn or make_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM company")

def add_company(company_data: dict, conn = None):
    conn = conn or make_connection()
    cursor = conn.cursor()

    # Define the SQL statement with placeholders (hardcoded columns)
    sql = """
        REPLACE INTO company (oid, title, address, town, searchstr, rating_2gis, trusted, nreviews, detections)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Extract values from the dictionary and map them to the placeholders
    cursor.execute(sql, (
        company_data.get("oid"), 
        company_data.get("title"), 
        company_data.get("address"), 
        company_data.get("town"), 
        company_data.get("searchstr").lower(), 
        company_data.get("rating_2gis"), 
        company_data.get("trusted"), 
        company_data.get("nreviews"), 
        company_data.get("detections")
    ))
    
    # Commit the transaction
    conn.commit()
