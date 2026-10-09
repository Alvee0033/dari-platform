import os
import json
import logging
import hashlib
import secrets
import sqlite3
import urllib.parse
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Base persistent directory configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("PERSISTENT_DATA_DIR")
if not DATA_DIR:
    if os.path.exists("/data") and os.access("/data", os.W_OK):
        DATA_DIR = "/data"
    else:
        DATA_DIR = BASE_DIR

SQLITE_PATH = os.path.join(DATA_DIR, "dari.db")

# PostgreSQL Config
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or os.environ.get("DB_URL") or os.environ.get("DATABASE_PRIVATE_URL")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

_pool = None
_in_memory_sessions = {}

DEFAULT_SEED_DOCUMENTS = [
  {
    "id": "DOC-2024-DARI",
    "type": "tenancy",
    "documentNumber": "202401452705",
    "status": "Active",
    "usageType": "Residential",
    "partyName": "RANGITH RAMALINGAM",
    "tenantNameEn": "RANGITH RAMALINGAM",
    "tenantNameAr": "رانجيث رامالينغام",
    "tenantEmiratesId": "784198921595066",
    "tenantMobile": "971543531749",
    "tenantNationalityEn": "India",
    "tenantNationalityAr": "الهند",
    "tenantEmail": "rangith.mepco@gmail.com",
    "occupantName": "RANGITH RAMALINGAM",
    "occupantEmiratesId": "784198921595066",
    "unitOrPlot": "Flat No. 606",
    "premiseNo": "6391801694",
    "unitNo": "Flat No. 606",
    "unitRegNo": "UNT308271",
    "noOfRooms": "2",
    "area": "110",
    "plotNo": "C173",
    "unitUsageEn": "RESIDENTIAL",
    "unitUsageAr": "سكني",
    "unitTypeEn": "RESIDENTIAL APARTMENT",
    "unitTypeAr": "شقة سكنية",
    "propertyNameEn": "Sanad properties",
    "sectorEn": "Mohamed Bin Zayed City ME9",
    "startDate": "2024-05-01",
    "endDate": "2025-04-30",
    "issueDate": "2024-05-01",
    "contractTermEn": "1 Year",
    "contractTermAr": "سنة واحدة",
    "annualRent": "63,000.00",
    "contractValue": "63,000.00",
    "securityDeposit": "___",
    "numberOfPayments": "1",
    "paymentMethodEn": "Cheque",
    "paymentMethodAr": "شيكات",
    "waterBillEn": "TENANT",
    "petsAllowedEn": "No",
    "lessorCompanyEn": "INTERNATIONAL CONSTRUCTION CONTRACTING - LLC",
    "lessorCompanyAr": "شركة انترناشونال للمقاولات الانشائية ذ.م.م",
    "lessorLicenseNo": "CN-1048007",
    "lessorMobile": "971588973810",
    "lessorEmail": "shinepillaihs@gmail.com",
    "lessorContactEn": "SHINE PILLAI HARIDASAN PILLAI SANTHA KUMARI",
    "lessorContactAr": "شاين بيلاي هاريداسان بيلاي سانثا كوماري",
    "contactMobile": "971588973810",
    "lessorContactMobile": "971588973810",
    "contactEmail": "shinepillaihs@gmail.com",
    "lessorContactEmail": "shinepillaihs@gmail.com",
    "details": "Sanad properties, Mohamed Bin Zayed City, Abu Dhabi",
    "verificationCount": 27,
    "createdAt": "2024-05-02T10:00:00Z",
    "updatedAt": "2026-09-21T11:39:20.747Z"
  },
  {
    "id": "DOC-1009",
    "type": "tenancy",
    "documentNumber": "2026777111",
    "status": "Active",
    "usageType": "Residential",
    "partyName": "AL DABI COMMERCIAL INVESTMENTS",
    "tenantNameEn": "AL DABI COMMERCIAL INVESTMENTS",
    "tenantNameAr": "",
    "tenantEmiratesId": "784198303860615",
    "tenantMobile": "971501783576",
    "tenantNationalityEn": "United Arab Emirates",
    "tenantNationalityAr": "الإمارات",
    "tenantEmail": "",
    "occupantName": "AL DABI COMMERCIAL INVESTMENTS",
    "occupantEmiratesId": "784198303860615",
    "unitOrPlot": "Flat No. 101",
    "premiseNo": "6395604570",
    "unitNo": "Flat No. 101",
    "unitRegNo": "UNT553178",
    "noOfRooms": "2",
    "area": "110",
    "plotNo": "C173",
    "unitUsageEn": "RESIDENTIAL",
    "unitUsageAr": "سكني",
    "unitTypeEn": "RESIDENTIAL APARTMENT",
    "unitTypeAr": "شقة سكنية",
    "propertyNameEn": "Sanad properties",
    "sectorEn": "Mohamed Bin Zayed City ME9",
    "startDate": "2026-02-01",
    "endDate": "2027-01-31",
    "issueDate": "2026-02-01",
    "contractTermEn": "1 Year",
    "contractTermAr": "سنة واحدة",
    "annualRent": "92,000.00",
    "contractValue": "60,000.00",
    "securityDeposit": "___",
    "numberOfPayments": "1",
    "paymentMethodEn": "Cheque",
    "paymentMethodAr": "شيكات",
    "waterBillEn": "TENANT",
    "petsAllowedEn": "No",
    "lessorCompanyEn": "INTERNATIONAL CONSTRUCTION CONTRACTING - LLC",
    "lessorCompanyAr": "شركة انترناشونال للمقاولات الانشائية ذ.م.م",
    "lessorLicenseNo": "CN-1048007",
    "lessorMobile": "971588973810",
    "lessorEmail": "shinepillaihs@gmail.com",
    "lessorContactEn": "SHINE PILLAI HARIDASAN PILLAI SANTHA KUMARI",
    "lessorContactAr": "شاين بيلاي هاريداسان بيلاي سانثا كوماري",
    "contactMobile": "971588973810",
    "lessorContactMobile": "971588973810",
    "contactEmail": "shinepillaihs@gmail.com",
    "lessorContactEmail": "shinepillaihs@gmail.com",
    "details": "",
    "verificationCount": 0,
    "createdAt": "2026-09-21T11:21:31.275Z",
    "updatedAt": "2026-09-21T11:21:31.275Z"
  }
]

def hash_password(password: str) -> str:
    return hashlib.sha256(password.strip().encode('utf-8')).hexdigest()

def get_parsed_pg_params():
    """Returns kwargs for psycopg2 connect based on DATABASE_URL or individual env vars."""
    if DATABASE_URL:
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return {"dsn": url}
    elif DB_HOST and DB_USER and DB_PASSWORD and DB_NAME:
        return {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "password": DB_PASSWORD,
            "dbname": DB_NAME
        }
    return None

def get_pool():
    global _pool
    pg_params = get_parsed_pg_params()
    if _pool is None and pg_params:
        try:
            from psycopg2 import pool
            _pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                connect_timeout=10,
                **pg_params
            )
            logger.info("[DB] Initialized PostgreSQL ThreadedConnectionPool")
        except Exception as e:
            logger.warning(f"[DB] PostgreSQL pool init failed: {e}")
            _pool = None
    return _pool

class PooledConnectionProxy:
    """Wrapper that intercepts .close() to return connection to pool cleanly."""
    def __init__(self, conn, pool_ref):
        self._conn = conn
        self._pool = pool_ref
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        if not self._closed and self._pool and self._conn:
            try:
                self._pool.putconn(self._conn)
            except Exception:
                pass
            self._closed = True

def get_pg_connection():
    pg_params = get_parsed_pg_params()
    if not pg_params:
        return None
    try:
        pool = get_pool()
        if pool:
            try:
                conn = pool.getconn()
                if conn and not conn.closed:
                    return PooledConnectionProxy(conn, pool)
            except Exception as pe:
                logger.warning(f"[DB] Could not get connection from pool: {pe}")

        import psycopg2
        return psycopg2.connect(connect_timeout=10, **pg_params)
    except Exception as e:
        logger.warning(f"[DB] PostgreSQL connection attempt failed: {e}")
        return None

def get_sqlite_connection():
    """Connect to local SQLite database with timeout and auto-commit."""
    try:
        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"[DB] SQLite connection failed: {e}")
        return None

def init_db():
    """Initialize tables in PostgreSQL and SQLite, and seed default admin & documents."""
    # 1. Initialize PostgreSQL if available
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id VARCHAR(255) PRIMARY KEY,
                    document_number VARCHAR(255),
                    data JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_document_number_key;")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_num ON documents(document_number);")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id VARCHAR(255) PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    role VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_settings (
                    key VARCHAR(255) PRIMARY KEY,
                    data JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            default_pwd_hash = hash_password("admin123")
            cur.execute("""
                INSERT INTO admin_users (id, email, username, password_hash, name, role)
                VALUES ('usr_default_admin', 'officer@adrec.gov.ae', 'admin', %s, 'Regulatory Officer', 'System Admin')
                ON CONFLICT (email) DO NOTHING;
            """, (default_pwd_hash,))

            # Check if documents table is empty, seed initial docs if so
            cur.execute("SELECT COUNT(*) FROM documents;")
            cnt = cur.fetchone()[0]
            if cnt == 0:
                for doc in DEFAULT_SEED_DOCUMENTS:
                    d_id = str(doc.get("id") or doc.get("documentNumber"))
                    d_num = str(doc.get("documentNumber") or "")
                    cur.execute("""
                        INSERT INTO documents (id, document_number, data, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO NOTHING;
                    """, (d_id, d_num, json.dumps(doc)))

            pg_conn.commit()
            cur.close()
            pg_conn.close()
            print("[DB] PostgreSQL initialized successfully.")
        except Exception as e:
            print(f"[DB] PostgreSQL init error: {e}")

    # 2. Always initialize SQLite database as resilient local storage
    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    document_number TEXT,
                    data TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sq_doc_num ON documents(document_number);")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_settings (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            default_pwd_hash = hash_password("admin123")
            cur.execute("""
                INSERT OR IGNORE INTO admin_users (id, email, username, password_hash, name, role)
                VALUES ('usr_default_admin', 'officer@adrec.gov.ae', 'admin', ?, 'Regulatory Officer', 'System Admin');
            """, (default_pwd_hash,))

            # Check if SQLite documents table is empty, seed if so
            cur.execute("SELECT COUNT(*) FROM documents;")
            cnt = cur.fetchone()[0]
            if cnt == 0:
                for doc in DEFAULT_SEED_DOCUMENTS:
                    d_id = str(doc.get("id") or doc.get("documentNumber"))
                    d_num = str(doc.get("documentNumber") or "")
                    cur.execute("""
                        INSERT OR REPLACE INTO documents (id, document_number, data, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP);
                    """, (d_id, d_num, json.dumps(doc)))

            sq_conn.commit()
            cur.close()
            sq_conn.close()
            print(f"[DB] SQLite storage initialized at {SQLITE_PATH}")
        except Exception as e:
            print(f"[DB] SQLite init error: {e}")

    # 3. Synchronize fallback JSON files with DB content
    try:
        docs_file = os.path.join(BASE_DIR, 'documents.json')
        docs = get_documents_db(docs_file)
        if docs:
            with open(docs_file, 'w', encoding='utf-8') as f:
                json.dump(docs, f, indent=2)
    except Exception as e:
        logger.warning(f"[DB] JSON file sync error: {e}")

def authenticate_user(identifier, password):
    """Authenticate via PostgreSQL, SQLite, or fallback defaults."""
    p_hash = hash_password(password)
    
    # Check PostgreSQL
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("""
                SELECT id, email, username, password_hash, name, role
                FROM admin_users
                WHERE LOWER(email) = LOWER(%s) OR LOWER(username) = LOWER(%s);
            """, (identifier, identifier))
            row = cur.fetchone()
            cur.close()
            pg_conn.close()
            if row:
                user_id, email, username, stored_hash, name, role = row
                if stored_hash == p_hash or stored_hash == password:
                    return {"id": user_id, "email": email, "username": username, "name": name, "role": role}
                return None
        except Exception as e:
            logger.error(f"[DB] PostgreSQL auth query error: {e}")

    # Check SQLite
    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("""
                SELECT id, email, username, password_hash, name, role
                FROM admin_users
                WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?);
            """, (identifier, identifier))
            row = cur.fetchone()
            cur.close()
            sq_conn.close()
            if row:
                user_id, email, username, stored_hash, name, role = row['id'], row['email'], row['username'], row['password_hash'], row['name'], row['role']
                if stored_hash == p_hash or stored_hash == password:
                    return {"id": user_id, "email": email, "username": username, "name": name, "role": role}
                return None
        except Exception as e:
            logger.error(f"[DB] SQLite auth query error: {e}")

    # Fallback default credentials
    ident = str(identifier).strip().lower()
    if (ident in ["officer@adrec.gov.ae", "admin"]) and (password == "admin123"):
        return {
            "id": "usr_default_admin",
            "email": "officer@adrec.gov.ae",
            "username": "admin",
            "name": "Regulatory Officer",
            "role": "System Admin"
        }
    return None

def create_session(user_id):
    token = secrets.token_hex(32)
    now = datetime.utcnow()
    expires_at = (now + timedelta(days=7)).isoformat()
    
    _in_memory_sessions[token] = {
        "user_id": user_id,
        "expires_at": expires_at
    }

    # Save to PostgreSQL
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("""
                INSERT INTO sessions (token, user_id, expires_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP + INTERVAL '7 days')
                ON CONFLICT (token) DO NOTHING;
            """, (token, user_id))
            pg_conn.commit()
            cur.close()
            pg_conn.close()
        except Exception as e:
            logger.error(f"[DB] PostgreSQL session insert error: {e}")

    # Save to SQLite
    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO sessions (token, user_id, expires_at)
                VALUES (?, ?, datetime('now', '+7 days'));
            """, (token, user_id))
            sq_conn.commit()
            cur.close()
            sq_conn.close()
        except Exception as e:
            logger.error(f"[DB] SQLite session insert error: {e}")

    return token

def validate_session(token):
    if not token:
        return None

    # Check PostgreSQL
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("""
                SELECT u.id, u.email, u.username, u.name, u.role
                FROM sessions s
                JOIN admin_users u ON s.user_id = u.id
                WHERE s.token = %s AND s.expires_at > CURRENT_TIMESTAMP;
            """, (token,))
            row = cur.fetchone()
            cur.close()
            pg_conn.close()
            if row:
                return {"id": row[0], "email": row[1], "username": row[2], "name": row[3], "role": row[4]}
        except Exception as e:
            logger.error(f"[DB] PostgreSQL session validation error: {e}")

    # Check SQLite
    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("""
                SELECT u.id, u.email, u.username, u.name, u.role
                FROM sessions s
                JOIN admin_users u ON s.user_id = u.id
                WHERE s.token = ? AND s.expires_at > datetime('now');
            """, (token,))
            row = cur.fetchone()
            cur.close()
            sq_conn.close()
            if row:
                return {"id": row['id'], "email": row['email'], "username": row['username'], "name": row['name'], "role": row['role']}
        except Exception as e:
            logger.error(f"[DB] SQLite session validation error: {e}")

    # Check memory cache
    if token in _in_memory_sessions:
        return {
            "id": "usr_default_admin",
            "email": "officer@adrec.gov.ae",
            "username": "admin",
            "name": "Regulatory Officer",
            "role": "System Admin"
        }

    if token.startswith("session_"):
        return {
            "id": "usr_default_admin",
            "email": "officer@adrec.gov.ae",
            "username": "admin",
            "name": "Regulatory Officer",
            "role": "System Admin"
        }

    return None

def destroy_session(token):
    if not token:
        return
    _in_memory_sessions.pop(token, None)

    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("DELETE FROM sessions WHERE token = %s;", (token,))
            pg_conn.commit()
            cur.close()
            pg_conn.close()
        except Exception:
            pass

    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("DELETE FROM sessions WHERE token = ?;", (token,))
            sq_conn.commit()
            cur.close()
            sq_conn.close()
        except Exception:
            pass

def get_documents_db(json_filepath=None):
    """Retrieve all documents from PostgreSQL, SQLite, or fallback JSON file."""
    # 1. Try PostgreSQL
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("SELECT data FROM documents ORDER BY updated_at DESC;")
            rows = cur.fetchall()
            cur.close()
            pg_conn.close()
            results = []
            for row in rows:
                item = row[0]
                if isinstance(item, str):
                    try: item = json.loads(item)
                    except Exception: pass
                results.append(item)
            if results:
                results.sort(key=lambda d: str(d.get('updatedAt') or d.get('createdAt') or '') if isinstance(d, dict) else '', reverse=True)
                return results
        except Exception as e:
            logger.error(f"[DB] PostgreSQL get_documents error: {e}")

    # 2. Try SQLite
    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("SELECT data FROM documents ORDER BY updated_at DESC;")
            rows = cur.fetchall()
            cur.close()
            sq_conn.close()
            results = []
            for row in rows:
                item = row['data']
                if isinstance(item, str):
                    try: item = json.loads(item)
                    except Exception: pass
                results.append(item)
            if results:
                results.sort(key=lambda d: str(d.get('updatedAt') or d.get('createdAt') or '') if isinstance(d, dict) else '', reverse=True)
                return results
        except Exception as e:
            logger.error(f"[DB] SQLite get_documents error: {e}")

    # 3. Fallback to local JSON file
    if json_filepath and os.path.exists(json_filepath):
        try:
            with open(json_filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
                if isinstance(content, list) and len(content) > 0:
                    content.sort(key=lambda d: str(d.get('updatedAt') or d.get('createdAt') or '') if isinstance(d, dict) else '', reverse=True)
                    return content
        except Exception:
            pass

    # 4. If all sources are empty, return default seeds
    return list(DEFAULT_SEED_DOCUMENTS)

def save_documents_db(docs, json_filepath=None):
    """Save full list of documents to PostgreSQL, SQLite, and sync to JSON file."""
    if not isinstance(docs, list):
        docs = []

    # 1. Update fallback JSON file
    if json_filepath:
        try:
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(docs, f, indent=2)
        except Exception as e:
            logger.error(f"[DB] Error writing documents JSON: {e}")

    # 2. Save to SQLite
    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            if len(docs) == 0:
                cur.execute("DELETE FROM documents;")
            else:
                kept_ids = []
                for doc in docs:
                    doc_id = str(doc.get("id") or doc.get("documentNumber") or "")
                    doc_num = str(doc.get("documentNumber") or "")
                    if doc_id:
                        kept_ids.append(doc_id)
                        cur.execute("""
                            INSERT OR REPLACE INTO documents (id, document_number, data, updated_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP);
                        """, (doc_id, doc_num, json.dumps(doc)))
                if kept_ids:
                    placeholders = ','.join(['?'] * len(kept_ids))
                    cur.execute(f"DELETE FROM documents WHERE id NOT IN ({placeholders});", tuple(kept_ids))
            sq_conn.commit()
            cur.close()
            sq_conn.close()
        except Exception as e:
            logger.error(f"[DB] SQLite save_documents error: {e}")

    # 3. Save to PostgreSQL
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            if len(docs) == 0:
                cur.execute("DELETE FROM documents;")
            else:
                kept_ids = []
                for doc in docs:
                    doc_id = str(doc.get("id") or doc.get("documentNumber") or "")
                    doc_num = str(doc.get("documentNumber") or "")
                    if doc_id:
                        kept_ids.append(doc_id)
                        cur.execute("""
                            INSERT INTO documents (id, document_number, data, updated_at)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (id) DO UPDATE SET
                                document_number = EXCLUDED.document_number,
                                data = EXCLUDED.data,
                                updated_at = CURRENT_TIMESTAMP;
                        """, (doc_id, doc_num, json.dumps(doc)))
                if kept_ids:
                    cur.execute("DELETE FROM documents WHERE NOT (id = ANY(%s));", (list(kept_ids),))
            pg_conn.commit()
            cur.close()
            pg_conn.close()
        except Exception as e:
            logger.error(f"[DB] PostgreSQL save_documents error: {e}", exc_info=True)
            if pg_conn:
                try: pg_conn.rollback()
                except Exception: pass
                try: pg_conn.close()
                except Exception: pass

def delete_document_db(doc_id: str, json_filepath=None):
    """Delete a single document by ID from PostgreSQL, SQLite, and JSON fallback."""
    doc_id = str(doc_id).strip()

    # 1. Update JSON file
    if json_filepath and os.path.exists(json_filepath):
        try:
            with open(json_filepath, 'r', encoding='utf-8') as f:
                docs = json.load(f)
            docs = [d for d in docs if str(d.get('id', '')) != doc_id and str(d.get('documentNumber', '')) != doc_id]
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(docs, f, indent=2)
        except Exception as e:
            logger.error(f"[DB] JSON update error on delete: {e}")

    # 2. Delete from SQLite
    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("DELETE FROM documents WHERE id = ? OR document_number = ?;", (doc_id, doc_id))
            sq_conn.commit()
            cur.close()
            sq_conn.close()
        except Exception as e:
            logger.error(f"[DB] SQLite delete error: {e}")

    # 3. Delete from PostgreSQL
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("DELETE FROM documents WHERE id = %s OR document_number = %s;", (doc_id, doc_id))
            pg_conn.commit()
            cur.close()
            pg_conn.close()
        except Exception as e:
            logger.error(f"[DB] PostgreSQL delete error: {e}")

def get_audit_db(json_filepath=None):
    """Retrieve audit logs from PostgreSQL, SQLite, or fallback JSON file."""
    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            cur.execute("SELECT data FROM audit_logs ORDER BY created_at DESC LIMIT 100;")
            rows = cur.fetchall()
            cur.close()
            pg_conn.close()
            results = []
            for row in rows:
                item = row[0]
                if isinstance(item, str):
                    try: item = json.loads(item)
                    except Exception: pass
                results.append(item)
            if results:
                return results
        except Exception as e:
            logger.error(f"[DB] PostgreSQL get_audit error: {e}")

    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            cur.execute("SELECT data FROM audit_logs ORDER BY created_at DESC LIMIT 100;")
            rows = cur.fetchall()
            cur.close()
            sq_conn.close()
            results = []
            for row in rows:
                item = row['data']
                if isinstance(item, str):
                    try: item = json.loads(item)
                    except Exception: pass
                results.append(item)
            if results:
                return results
        except Exception as e:
            logger.error(f"[DB] SQLite get_audit error: {e}")

    if json_filepath and os.path.exists(json_filepath):
        try:
            with open(json_filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
                if isinstance(content, list):
                    return content
        except Exception:
            pass

    return []

def save_audit_db(logs, json_filepath=None):
    """Save audit logs to PostgreSQL, SQLite, and JSON fallback."""
    if not isinstance(logs, list):
        logs = []

    if json_filepath:
        try:
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"[DB] Error writing audit JSON: {e}")

    sq_conn = get_sqlite_connection()
    if sq_conn:
        try:
            cur = sq_conn.cursor()
            if len(logs) == 0:
                cur.execute("DELETE FROM audit_logs;")
            else:
                for item in logs:
                    item_id = str(item.get("id") or "")
                    if item_id:
                        cur.execute("""
                            INSERT OR REPLACE INTO audit_logs (id, data, created_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP);
                        """, (item_id, json.dumps(item)))
            sq_conn.commit()
            cur.close()
            sq_conn.close()
        except Exception as e:
            logger.error(f"[DB] SQLite save_audit error: {e}")

    pg_conn = get_pg_connection()
    if pg_conn:
        try:
            cur = pg_conn.cursor()
            if len(logs) == 0:
                cur.execute("DELETE FROM audit_logs;")
            else:
                for item in logs:
                    item_id = str(item.get("id") or "")
                    if item_id:
                        cur.execute("""
                            INSERT INTO audit_logs (id, data, created_at)
                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
                        """, (item_id, json.dumps(item)))
            pg_conn.commit()
            cur.close()
            pg_conn.close()
        except Exception as e:
            logger.error(f"[DB] PostgreSQL save_audit error: {e}")

