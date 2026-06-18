import os
import firebase_admin
from firebase_admin import credentials, firestore

# Mengambil environment variable dari folder root atau internal backend
if os.path.exists("backend/.env"):
    from dotenv import load_dotenv
    load_dotenv("backend/.env")
else:
    from dotenv import load_dotenv
    load_dotenv()

def init_firebase():
    """Inisialisasi Firebase Admin SDK menggunakan kredensial dari .env"""
    try:
        return firebase_admin.get_app()
    except ValueError:
        private_key = os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
        
        cred_dict = {
            "type": "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": private_key,
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        cred = credentials.Certificate(cred_dict)
        return firebase_admin.initialize_app(cred)

# Jalankan inisialisasi cloud database
init_firebase()
db = firestore.client()

# ═══ MOCK OBYEK UNTUK BYPASS ERROR IMPORT SQLALCHEMY ════════
class MockEngine:
    def begin(self):
        """Dummy context manager biar lifespan main.py tidak crash"""
        class DummyContext:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            async def run_sync(self, func, *args, **kwargs): pass
        return DummyContext()

engine = MockEngine()

def AsyncSessionLocal():
    pass

class Base:
    metadata = None

# 🚀 MOCK DEPENDENCY GET_DB (SUNTIKAN PENYELAMAT ROUTER LAMA)
async def get_db():
    """Dummy dependency generator agar router predict/analytics timmu tidak melempar ImportError"""
    class DummySession:
        async def rollback(self): pass
        async def commit(self): pass
        async def close(self): pass
    
    yield DummySession()