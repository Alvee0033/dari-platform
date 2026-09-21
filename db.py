import os
import json
import logging

logger = logging.getLogger(__name__)

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

def get_db_connection():
    if not (DB_HOST and DB_USER and DB_PASSWORD and DB_NAME):
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            connect_timeout=5
        )
        return conn
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        print("[DB] PostgreSQL not configured or unreachable, using local JSON storage.")
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR(255) PRIMARY KEY,
                document_number VARCHAR(255) UNIQUE,
                data JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id VARCHAR(255) PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("[DB] PostgreSQL database initialized successfully.")
    except Exception as e:
        print(f"[DB] Init error: {e}")

def get_documents_db(json_filepath):
    conn = get_db_connection()
    if not conn:
        if os.path.exists(json_filepath):
            with open(json_filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT data FROM documents ORDER BY updated_at DESC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error fetching documents from DB: {e}")

    # Fallback to local file if empty or error
    if os.path.exists(json_filepath):
        with open(json_filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_documents_db(docs, json_filepath):
    # Always save to json file locally as cache/seed
    try:
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing local json: {e}")

    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        for doc in docs:
            doc_id = str(doc.get("id") or doc.get("documentNumber") or "")
            doc_num = str(doc.get("documentNumber") or "")
            if doc_id:
                cur.execute("""
                    INSERT INTO documents (id, document_number, data, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        document_number = EXCLUDED.document_number,
                        data = EXCLUDED.data,
                        updated_at = CURRENT_TIMESTAMP;
                """, (doc_id, doc_num, json.dumps(doc)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving documents to DB: {e}")

def get_audit_db(json_filepath):
    conn = get_db_connection()
    if not conn:
        if os.path.exists(json_filepath):
            with open(json_filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT data FROM audit_logs ORDER BY created_at DESC LIMIT 100;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if rows:
            return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error fetching audit log from DB: {e}")

    if os.path.exists(json_filepath):
        with open(json_filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_audit_db(logs, json_filepath):
    try:
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing local audit json: {e}")

    conn = get_db_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        for item in logs:
            item_id = str(item.get("id") or "")
            if item_id:
                cur.execute("""
                    INSERT INTO audit_logs (id, data, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        data = EXCLUDED.data;
                """, (item_id, json.dumps(item)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving audit log to DB: {e}")
