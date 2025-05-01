import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a connection pool
connection_pool = psycopg2.pool.SimpleConnectionPool(
    1,  # Minimum connections
    20,  # Maximum connections
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

def get_db_connection():
    """Get a connection from the pool"""
    return connection_pool.getconn()

def release_db_connection(conn):
    """Release a connection back to the pool"""
    connection_pool.putconn(conn)

def execute_query(query, params=None, fetch=True):
    """Execute a database query and return results"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch:
            results = cursor.fetchall()
        else:
            conn.commit()
            results = None
            
        cursor.close()
        return results
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            release_db_connection(conn)
